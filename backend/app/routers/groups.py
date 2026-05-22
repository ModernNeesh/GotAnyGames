from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.models.schemas import (
    CreateGroupRequest,
    ExistingGroupModel,
    ExistingUserModel,
    GroupIdRequest,
    RenameGroupRequest,
)
from app.models.db import User as UserDB, Group as GroupDB
from app.database import Session

router = APIRouter(tags=["groups"])


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


@router.delete("/leave_group/")
def leave_group(
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

        group.users.remove(user)
        session.commit()
        session.refresh(user)
        session.refresh(group)

    return {
        "user": ExistingUserModel.model_validate(user),
        "group": ExistingGroupModel.model_validate(group),
    }


@router.patch("/rename_group/")
def rename_group(body: RenameGroupRequest) -> ExistingGroupModel:
    with Session() as session:
        group = session.get(GroupDB, body.id)

        if group is None:
            raise HTTPException(status_code=404, detail="Group does not exist")

        group.name = body.name
        session.commit()
        session.refresh(group)

    return ExistingGroupModel.model_validate(group)
