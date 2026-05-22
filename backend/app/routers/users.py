from fastapi import APIRouter, HTTPException
from app.models.schemas import NewUserModel, ExistingUserModel, UserPrefModel
from app.models.db import User as UserDB, UserPref as UserPrefDB
from app.database import Session
import pandas as pd

router = APIRouter(tags=["users"])


@router.post("/create_user/")
def create_user(user: dict):
    user_model = NewUserModel.model_validate(user)

    with Session() as session:
        user_db_row = UserDB(name=user_model.name)
        session.add(user_db_row)
        session.commit()
        session.refresh(user_db_row)

    return ExistingUserModel.model_validate(user_db_row)


@router.patch("/rename_user/")
def rename_user(user_rename: dict):
    user_rename_model = ExistingUserModel.model_validate(user_rename)

    with Session() as session:
        user = session.get(UserDB, user_rename_model.group_id)

        if user is None:
            raise HTTPException(status_code=404, detail="User does not exist")

        user.name = user_rename_model.name
        session.commit()
        session.refresh(user)

    return ExistingUserModel.model_validate(user)


@router.post("/add_user_prefs/")
def add_user_prefs(user_prefs: dict):
    prefs_model = UserPrefModel.model_validate(user_prefs)
    prefs_df = pd.DataFrame(prefs_model.model_dump()).explode(column=["platform_id", "online", "offline"])

    with Session() as session:
        session.bulk_insert_mappings(UserPrefDB, prefs_df.to_dict(orient="records"))
        session.commit()

    return prefs_model
