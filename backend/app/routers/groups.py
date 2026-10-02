from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.auth import get_current_user
from app.group_preferences import summarize_group_preferences
from app.models.schemas import (
    CreateGroupRequest,
    AddGroupMemberRequest,
    ExistingGroupModel,
    ExistingUserModel,
    GroupDetailModel,
    GroupIdRequest,
    GroupPlatformModel,
    GroupPlatformPreferenceModel,
    GroupPreferencesModel,
    GroupPreferencesRequest,
    GroupPreferenceSummaryModel,
    RenameGroupRequest,
)
from app.models.db import (
    User as UserDB,
    Group as GroupDB,
    GroupUserPreference,
    Platform,
    group_membership,
)
from app.database import Session

router = APIRouter(tags=["groups"])


#Helper functions for group data retrieval


def require_group_member(session, group_id: int, user_id: UUID, *, lock: bool = False) -> GroupDB:
    """
    Checks if user is a member of the specified group, throws an error if not.

    Inputs:
    session (Session): The SQLAlchemy session for database access.
    group_id (int): The unique identifier of the group to check.
    user_id (UUID): The unique identifier of the user to check membership for.
    lock (bool): Serialize preference saves and member departures for this group.

    Returns:

    GroupDB: The group object if the user is a member (rarely used)
    """

    if lock:
        # Acquire the group lock before checking membership in a separate query.
        # A save waiting for a removal must see that membership's committed deletion.
        session.query(GroupDB.id).filter(GroupDB.id == group_id).with_for_update().first()

    group = (
        session.query(GroupDB)
        .join(group_membership, group_membership.c.group_id == GroupDB.id)
        .filter(GroupDB.id == group_id, group_membership.c.user_id == user_id)
        .first()
    )
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def group_detail(group: GroupDB) -> GroupDetailModel:
    """
    Returns group details sorted by member display name first and UUID second

    Inputs:
    group (GroupDB): The group object to serialize.

    Returns:

    GroupDetailModel: The serialized group detail model with sorted members.
    """
    members = sorted(group.users, key=lambda member: (member.name.casefold(), str(member.id)))
    return GroupDetailModel(
        id=group.id,
        name=group.name,
        members=[ExistingUserModel.model_validate(member) for member in members],
    )


def group_preferences(session, group_id: int, user_id: UUID) -> GroupPreferencesModel:
    """Read one user's saved preferences in one group, ordered by platform ID.

    Inputs:
    group_id (int): The unique identifier of the group to retrieve preferences for.
    user_id (UUID): The unique identifier of the user whose preferences are being retrieved.

    Returns:

    GroupPreferencesModel: The serialized group preferences model for the specified user in the specified group.
    """
    rows = (
        session.query(GroupUserPreference)
        .filter_by(group_id=group_id, user_id=user_id)
        .order_by(GroupUserPreference.platform_id)
        .all()
    )
    return GroupPreferencesModel(
        platforms=[GroupPlatformPreferenceModel.model_validate(row) for row in rows],
    )


#API routes


#List the authenticated user's groups in name and ID order.
@router.get("/my_groups/")
def get_my_groups(
    user_id: UUID = Depends(get_current_user),
) -> list[ExistingGroupModel]:

    with Session() as session:
        groups = (
            session.query(GroupDB)
            .join(group_membership, group_membership.c.group_id == GroupDB.id)
            .filter(group_membership.c.user_id == user_id)
            .order_by(GroupDB.name, GroupDB.id)
            .all()
        )
        return [ExistingGroupModel.model_validate(group) for group in groups]

#Get the group's ID, name, and member list for the group detail page.
@router.get("/groups/{group_id}")
def get_group(group_id: int, user_id: UUID = Depends(get_current_user)) -> GroupDetailModel:

    with Session() as session:
        return group_detail(require_group_member(session, group_id, user_id))

#List the existing platform catalog for the preferences picker.
@router.get("/group_platforms/")
def get_group_platforms(
    user_id: UUID = Depends(get_current_user),
) -> list[GroupPlatformModel]:


    with Session() as session:
        platforms = session.query(Platform).order_by(func.lower(Platform.name), Platform.id).all()
        return [GroupPlatformModel.model_validate(platform) for platform in platforms]

#Return a list of existing users that can be added to the group.
@router.get("/groups/{group_id}/users")
def search_group_users(
    group_id: int,
    query: str = Query(min_length=2, max_length=100),
    user_id: UUID = Depends(get_current_user),
) -> list[ExistingUserModel]:

    with Session() as session:
        require_group_member(session, group_id, user_id)
        query = query.strip()
        if len(query) < 2:
            raise HTTPException(status_code=422, detail="Enter at least two characters")
        #IDs of users currently in the group
        members = (
            session.query(group_membership.c.user_id)
            .filter(group_membership.c.group_id == group_id)
        )

        #All users not currently in the group
        users = (
            session.query(UserDB)
            # Escape SQL LIKE wildcards so '%' and '_' are searched literally.
            .filter(UserDB.name.icontains(query, autoescape=True), UserDB.id.notin_(members))
            .order_by(func.lower(UserDB.name), UserDB.id)
            .limit(20)
            .all()
        )
        return [ExistingUserModel.model_validate(user) for user in users]

#Add an existing user and return the refreshed member list.
@router.post("/groups/{group_id}/members")
def add_group_member(
    group_id: int,
    body: AddGroupMemberRequest,
    user_id: UUID = Depends(get_current_user),
) -> GroupDetailModel:

    with Session() as session:
        group = require_group_member(session, group_id, user_id) # Ensure caller is in group
        member = session.get(UserDB, body.user_id)
        if member is None:
            raise HTTPException(status_code=404, detail="User not found")
        if member in group.users:
            raise HTTPException(status_code=409, detail="User is already in this group")
        group.users.append(member)
        try:
            session.commit()
        except IntegrityError:
            # Another request can add the same user after the duplicate check.
            session.rollback()
            raise HTTPException(status_code=409, detail="Group membership changed. Refresh and try again")
        return group_detail(group)

#Allow any current member to remove another member and their group preferences.
@router.delete("/groups/{group_id}/members/{member_id}")
def remove_group_member(
    group_id: int,
    member_id: UUID,
    user_id: UUID = Depends(get_current_user),
) -> GroupDetailModel:

    with Session() as session:
        group = require_group_member(session, group_id, user_id, lock=True)
        if member_id == user_id:
            raise HTTPException(status_code=400, detail="Use the leave group action to remove yourself")

        removed = session.execute(
            group_membership.delete().where(
                group_membership.c.group_id == group_id,
                group_membership.c.user_id == member_id,
            )
        )
        if removed.rowcount == 0:
            raise HTTPException(status_code=404, detail="Group member not found")

        session.query(GroupUserPreference).filter_by(group_id=group_id, user_id=member_id).delete()
        session.commit()
        return group_detail(group)

#Read a group member's preferences for this group.
@router.get("/groups/{group_id}/members/{member_id}/preferences")
def get_group_member_preferences(
    group_id: int,
    member_id: UUID,
    user_id: UUID = Depends(get_current_user),
) -> GroupPreferencesModel:

    with Session() as session:
        #Ensure both the caller and the requested member belong to the group
        require_group_member(session, group_id, user_id)
        require_group_member(session, group_id, member_id)

        return group_preferences(session, group_id, member_id)

#Read aggregate preferences for current group members.
@router.get("/groups/{group_id}/preferences/summary")
def get_group_preference_summary(
    group_id: int,
    user_id: UUID = Depends(get_current_user),
) -> GroupPreferenceSummaryModel:

    with Session() as session:
        require_group_member(session, group_id, user_id)
        return summarize_group_preferences(session, group_id)

#Replace the caller's full preference selection for this group.
@router.patch("/groups/{group_id}/preferences")
def update_group_preferences(
    group_id: int,
    body: GroupPreferencesRequest,
    user_id: UUID = Depends(get_current_user),
) -> GroupPreferencesModel:

    with Session() as session:
        require_group_member(session, group_id, user_id, lock=True)
        #Make sure the platforms in the request actually exist
        platform_ids = [platform.platform_id for platform in body.platforms]
        valid_platform_count = (
            session.query(Platform)
            .filter(Platform.id.in_(platform_ids))
            .count()
        )
        if valid_platform_count != len(platform_ids):
            raise HTTPException(status_code=422, detail="One or more platforms do not exist")


        session.query(GroupUserPreference).filter_by(group_id=group_id, user_id=user_id).delete()
        session.add_all([
            GroupUserPreference(
                group_id=group_id,
                user_id=user_id,
                platform_id=platform.platform_id,
                online=platform.online,
                offline=platform.offline,
            )
            for platform in body.platforms
        ])
        session.commit()
        return group_preferences(session, group_id, user_id)

#Create a named group and automatically add the creator.
@router.post("/create_group/")
def create_group(
    body: CreateGroupRequest,
    user_id: UUID = Depends(get_current_user),
) -> ExistingGroupModel:

    with Session() as session:
        group_db_row = GroupDB(name=body.name)
        creator = session.get(UserDB, user_id)

        if creator is None:
            raise HTTPException(status_code=404, detail="Creator user not found")

        group_db_row.users.append(creator)
        session.add(group_db_row)
        session.commit()
        session.refresh(group_db_row)

    return ExistingGroupModel.model_validate(group_db_row)


#Join an existing group. Does not require another member to add the user.
@router.post("/join_group/")
def join_group(
    body: GroupIdRequest,
    user_id: UUID = Depends(get_current_user),
):

    with Session() as session:
        user = session.get(UserDB, user_id)
        group = session.get(GroupDB, body.group_id)

        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")

        if group is None:
            raise HTTPException(status_code=404, detail="Group does not exist")

        group.users.append(user)
        session.commit()
        session.refresh(user)
        session.refresh(group)

    return {
        "user": ExistingUserModel.model_validate(user),
        "group": ExistingGroupModel.model_validate(group),
    }


#Remove the caller's membership and preferences for the selected group.
@router.delete("/leave_group/")
def leave_group(
    body: GroupIdRequest,
    user_id: UUID = Depends(get_current_user),
):

    with Session() as session:
        user = session.get(UserDB, user_id)
        group = require_group_member(session, body.group_id, user_id, lock=True)
        session.query(GroupUserPreference).filter_by(group_id=body.group_id, user_id=user_id).delete()
        group.users.remove(user)
        session.commit()
        session.refresh(user)
        session.refresh(group)

    return {
        "user": ExistingUserModel.model_validate(user),
        "group": ExistingGroupModel.model_validate(group),
    }

#Rename a group after checking the authenticated caller's membership.
@router.patch("/rename_group/")
def rename_group(
    body: RenameGroupRequest,
    user_id: UUID = Depends(get_current_user),
) -> ExistingGroupModel:

    with Session() as session:
        group = require_group_member(session, body.id, user_id)
        group.name = body.name
        session.commit()
        session.refresh(group)

    return ExistingGroupModel.model_validate(group)
