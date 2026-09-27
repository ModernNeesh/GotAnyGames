"""Group membership, detail-page data, and per-group player preferences.

The acting user's UUID always comes from the verified authentication token.
The detail-page routes check membership before accessing a group's data; any
member can add another existing user or rename the group. The legacy join route
still permits self-joining by group ID. See backend/docs/groups.md for the API
contract, storage model, and permission rules.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.auth import get_current_user
from app.models.schemas import (
    CreateGroupRequest,
    AddGroupMemberRequest,
    ExistingGroupModel,
    ExistingUserModel,
    GroupDetailModel,
    GroupIdRequest,
    GroupPlatformModel,
    GroupPreferencesModel,
    GroupPreferencesRequest,
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


def require_group_member(session, group_id: int, user_id: UUID) -> GroupDB:
    """Return the group only when the supplied user belongs to it.

    Missing groups and missing memberships both return the same 404 response,
    so these reads do not reveal whether an inaccessible group exists. The
    caller owns the session and must keep it open when loading group.users.
    """
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
    """Serialize a group and its members while the ORM session is open.

    Sort members by case-insensitive display name, then UUID for stable ordering
    when names match. Only member UUIDs and display names are returned.
    """
    members = sorted(group.users, key=lambda member: (member.name.casefold(), str(member.id)))
    return GroupDetailModel(
        id=group.id,
        name=group.name,
        members=[ExistingUserModel.model_validate(member) for member in members],
    )


def group_preferences(session, group_id: int, user_id: UUID) -> GroupPreferencesModel:
    """Read one user's saved preferences in one group, ordered by platform ID.

    Storage has one row per selected platform. The update endpoint writes the
    same play-mode flags to every row; this response combines them with any().
    With no saved rows, return an empty platform list and both flags false.
    Membership must be checked by the calling route before using this helper.
    """
    rows = (
        session.query(GroupUserPreference)
        .filter_by(group_id=group_id, user_id=user_id)
        .order_by(GroupUserPreference.platform_id)
        .all()
    )
    return GroupPreferencesModel(
        platform_ids=[row.platform_id for row in rows],
        online=any(row.online for row in rows),
        offline=any(row.offline for row in rows),
    )


#Get groups the authenticated user belongs to
@router.get("/my_groups/")
def get_my_groups(
    user_id: UUID = Depends(get_current_user),
) -> list[ExistingGroupModel]:
    """List the authenticated user's groups in name and ID order.

    The caller cannot select another user's groups through a request parameter.
    A user with no memberships receives an empty list.
    """
    with Session() as session:
        groups = (
            session.query(GroupDB)
            .join(group_membership, group_membership.c.group_id == GroupDB.id)
            .filter(group_membership.c.user_id == user_id)
            .order_by(GroupDB.name, GroupDB.id)
            .all()
        )
        return [ExistingGroupModel.model_validate(group) for group in groups]


@router.get("/groups/{group_id}")
def get_group(group_id: int, user_id: UUID = Depends(get_current_user)) -> GroupDetailModel:
    """Get the group's ID, name, and member list for the group detail page.

    Requires membership; returns 404 for a missing or inaccessible group.
    """
    with Session() as session:
        return group_detail(require_group_member(session, group_id, user_id))


@router.get("/group_platforms/")
def get_group_platforms(
    user_id: UUID = Depends(get_current_user),
) -> list[GroupPlatformModel]:
    """List the existing platform catalog for the preferences picker.

    Requires authentication, but no particular group membership. Returns
    platform IDs and names sorted by case-insensitive name, then ID.
    """
    with Session() as session:
        platforms = session.query(Platform).order_by(func.lower(Platform.name), Platform.id).all()
        return [GroupPlatformModel.model_validate(platform) for platform in platforms]


@router.get("/groups/{group_id}/users")
def search_group_users(
    group_id: int,
    query: str = Query(min_length=2, max_length=100),
    user_id: UUID = Depends(get_current_user),
) -> list[ExistingUserModel]:
    """Find existing users a member can add to this group by display name.

    The query must contain 2-100 characters before trimming and at least two
    afterward. Match a case-insensitive literal substring, exclude current
    members, and return at most 20 results in name/UUID order. The response
    includes only each user's UUID and display name, not authentication data.
    """
    with Session() as session:
        require_group_member(session, group_id, user_id)
        query = query.strip()
        if len(query) < 2:
            raise HTTPException(status_code=422, detail="Enter at least two characters")
        members = (
            session.query(group_membership.c.user_id)
            .filter(group_membership.c.group_id == group_id)
        )
        users = (
            session.query(UserDB)
            # Escape SQL LIKE wildcards so '%' and '_' are searched literally.
            .filter(UserDB.name.icontains(query, autoescape=True), UserDB.id.notin_(members))
            .order_by(func.lower(UserDB.name), UserDB.id)
            .limit(20)
            .all()
        )
        return [ExistingUserModel.model_validate(user) for user in users]


@router.post("/groups/{group_id}/members")
def add_group_member(
    group_id: int,
    body: AddGroupMemberRequest,
    user_id: UUID = Depends(get_current_user),
) -> GroupDetailModel:
    """Add an existing user immediately and return the refreshed member list.

    The authenticated caller must already belong to the group. body.user_id is
    the target user's UUID, not the caller's identity. Any member may add users;
    this is direct membership creation, with no invitation or owner workflow.
    Return 404 for an unknown target and 409 for a duplicate or conflicting add.
    """
    with Session() as session:
        group = require_group_member(session, group_id, user_id)
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


@router.get("/groups/{group_id}/members/{member_id}/preferences")
def get_group_member_preferences(
    group_id: int,
    member_id: UUID,
    user_id: UUID = Depends(get_current_user),
) -> GroupPreferencesModel:
    """Read a fellow member's preferences for this group, including your own.

    Both the caller and requested member must belong to the group. No saved
    preferences returns {platform_ids: [], online: false, offline: false}.
    These settings are separate from the user's global UserPref records.
    """
    with Session() as session:
        require_group_member(session, group_id, user_id)
        require_group_member(session, group_id, member_id)
        return group_preferences(session, group_id, member_id)


@router.patch("/groups/{group_id}/preferences")
def update_group_preferences(
    group_id: int,
    body: GroupPreferencesRequest,
    user_id: UUID = Depends(get_current_user),
) -> GroupPreferencesModel:
    """Replace the caller's full preference selection for this group.

    Requires at least one unique, positive platform ID and one enabled play
    mode. The schema validates types; this route checks platform existence.
    Both flags apply to every selected platform. Validate before deleting old
    rows, then replace them in one transaction. Other groups, other members,
    and global user preferences are unaffected. Returns the saved selection.
    """
    with Session() as session:
        require_group_member(session, group_id, user_id)
        valid_platform_count = (
            session.query(Platform)
            .filter(Platform.id.in_(body.platform_ids))
            .count()
        )
        if valid_platform_count != len(body.platform_ids):
            raise HTTPException(status_code=422, detail="One or more platforms do not exist")
        # A save is a complete replacement, scoped to the JWT user and this group.
        session.query(GroupUserPreference).filter_by(group_id=group_id, user_id=user_id).delete()
        session.add_all([
            GroupUserPreference(
                group_id=group_id,
                user_id=user_id,
                platform_id=platform_id,
                online=body.online,
                offline=body.offline,
            )
            for platform_id in body.platform_ids
        ])
        session.commit()
        return group_preferences(session, group_id, user_id)


#Create a group
@router.post("/create_group/")
def create_group(
    body: CreateGroupRequest,
    user_id: UUID = Depends(get_current_user),
) -> ExistingGroupModel:
    """Create a named group and automatically add the authenticated creator.

    The request schema trims the name and requires 1-100 characters. The user
    must already have an app User row from /auth/sync; otherwise return 404.
    Return the new group's ID and name so the UI can navigate to its page.
    """
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



#Join a group
@router.post("/join_group/")
def join_group(
    body: GroupIdRequest,
    user_id: UUID = Depends(get_current_user),
):
    """Join an existing group as the authenticated user by its numeric ID.

    This existing route is retained for compatibility. It does not implement
    invitations or require approval from another member, and the new group
    page uses the member-only add-user route instead.
    """
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



#Leave a group
@router.delete("/leave_group/")
def leave_group(
    body: GroupIdRequest,
    user_id: UUID = Depends(get_current_user),
):
    """Remove the caller's membership and preferences for the selected group.

    Require an existing membership and delete its preference rows in the same
    transaction. Preserve other users' settings and the group itself, even
    when its final member leaves. Return the existing {user, group} response.
    """
    with Session() as session:
        user = session.get(UserDB, user_id)
        group = require_group_member(session, body.group_id, user_id)
        session.query(GroupUserPreference).filter_by(group_id=body.group_id, user_id=user_id).delete()
        group.users.remove(user)
        session.commit()
        session.refresh(user)
        session.refresh(group)

    return {
        "user": ExistingUserModel.model_validate(user),
        "group": ExistingGroupModel.model_validate(group),
    }


#Rename a group
@router.patch("/rename_group/")
def rename_group(
    body: RenameGroupRequest,
    user_id: UUID = Depends(get_current_user),
) -> ExistingGroupModel:
    """Rename a group after checking the authenticated caller's membership.

    Any member can rename it; there is no owner role. The same trimmed 1-100
    character name validation used for creation applies here. Return ID/name.
    """
    with Session() as session:
        group = require_group_member(session, body.id, user_id)
        group.name = body.name
        session.commit()
        session.refresh(group)

    return ExistingGroupModel.model_validate(group)
