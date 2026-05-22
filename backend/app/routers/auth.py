from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models.db import User as UserDB
from app.models.schemas import AuthSyncResponse
from app.database import Session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/sync")
def sync_user(
    display_name: str,
    user_id: UUID = Depends(get_current_user),
) -> AuthSyncResponse:
    with Session() as session:
        user = session.get(UserDB, user_id)
        if user is None:
            user = UserDB(id=user_id, name=display_name)
            session.add(user)
        else:
            user.name = display_name
        session.commit()
        session.refresh(user)
    return AuthSyncResponse.model_validate(user)
