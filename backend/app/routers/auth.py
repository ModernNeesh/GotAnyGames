from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models.db import User as UserDB
from app.models.schemas import AuthSyncResponse
from app.database import Session

router = APIRouter(prefix="/auth", tags=["auth"])



@router.post("/sync")
def sync_user(
    auto_display_name: str,
    user_id: UUID = Depends(get_current_user),
) -> AuthSyncResponse:
    """
    Ensure user exists in table, and give them an automatically generated username if not.
    If they already exists, no need to do anything.

    Inputs:
    - auto_display_name: Automatically generated display name for the user
    - user_id: UUID of the user (obtained from the JWT token)
    """
    with Session() as session:
        user = session.get(UserDB, user_id)
        if user is None:
            user = UserDB(id=user_id, name=auto_display_name)
            session.add(user)
        session.commit()
        session.refresh(user)
    return AuthSyncResponse.model_validate(user)
