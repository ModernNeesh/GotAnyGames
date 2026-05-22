from fastapi import APIRouter, HTTPException
from app.models.schemas import NewGroupModel, ExistingGroupModel, GroupJoin, ExistingUserModel
from app.models.db import User as UserDB, Group as GroupDB
from app.database import Session

router = APIRouter(tags=["groups"])


@router.post("/create_group/")
def create_group(group_init: dict):
    group_model = NewGroupModel.model_validate(group_init)

    with Session() as session:
        group_db_row = GroupDB(name=group_model.name)
        creator = session.get(UserDB, group_model.user_id)

        if creator is None:
            raise HTTPException(status_code=404, detail="Creator user not found")

        group_db_row.users.append(creator)
        session.add(group_db_row)
        session.commit()
        session.refresh(group_db_row)

    return ExistingGroupModel.model_validate(group_db_row)


@router.post("/join_group/")
def join_group(group_join: dict):
    group_join_model = GroupJoin.model_validate(group_join)

    with Session() as session:
        user = session.get(UserDB, group_join_model.user_id)
        group = session.get(GroupDB, group_join_model.group_id)

        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")

        if group is None:
            raise HTTPException(status_code=404, detail="Group does not exist")

        group.users.append(user)
        session.commit()
        session.refresh(user)
        session.refresh(group)

    return {"user": ExistingUserModel.model_validate(user), "group": ExistingGroupModel.model_validate(group)}


@router.delete("/leave_group/")
def leave_group(group_leave: dict):
    group_leave_model = GroupJoin.model_validate(group_leave)

    with Session() as session:
        user = session.get(UserDB, group_leave_model.user_id)
        group = session.get(GroupDB, group_leave_model.group_id)

        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")

        if group is None:
            raise HTTPException(status_code=404, detail="Group does not exist")

        group.users.remove(user)
        session.commit()
        session.refresh(user)
        session.refresh(group)

    return {"user": ExistingUserModel.model_validate(user), "group": ExistingGroupModel.model_validate(group)}


@router.patch("/rename_group/")
def rename_group(group_rename: dict):
    group_rename_model = ExistingGroupModel.model_validate(group_rename)

    with Session() as session:
        group = session.get(GroupDB, group_rename_model.group_id)

        if group is None:
            raise HTTPException(status_code=404, detail="Group does not exist")

        group.name = group_rename_model.name
        session.commit()
        session.refresh(group)

    return ExistingGroupModel.model_validate(group)
