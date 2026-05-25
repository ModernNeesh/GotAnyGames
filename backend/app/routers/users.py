from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
import pandas as pd

from app.auth import get_current_user
from app.models.schemas import RenameRequest, ExistingUserModel, UserPrefRequest
from app.models.db import User as UserDB, UserPref as UserPrefDB
from app.database import Session

router = APIRouter(tags=["users"])


#Rename a user
@router.patch("/rename_user/")
def rename_user(
    body: RenameRequest,
    user_id: UUID = Depends(get_current_user),
) -> ExistingUserModel:
    with Session() as session:
        user = session.get(UserDB, user_id)

        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")

        user.name = body.name
        session.commit()
        session.refresh(user)

    return ExistingUserModel.model_validate(user)


#Add a user's preferences
@router.post("/add_user_prefs/")
def add_user_prefs(
    body: UserPrefRequest,
    user_id: UUID = Depends(get_current_user),
):
    records = [
        {"user_id": user_id, "platform_id": pid, "online": on, "offline": off}
        for pid, on, off in zip(body.platform_id, body.online, body.offline)
    ]

    with Session() as session:
        session.bulk_insert_mappings(UserPrefDB, records)
        session.commit()

    return body
