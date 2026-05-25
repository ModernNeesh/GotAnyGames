from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import joinedload

from app.auth import get_current_user
from app.models.schemas import RateGameRequest, UserRatedGame
from app.models.db import UserRating as UserRatingDB, Game
from app.database import Session

router = APIRouter(tags=["ratings"])


#Get ratings made by given user
@router.get("/my_ratings/")
def get_my_ratings(
    user_id: UUID = Depends(get_current_user),
) -> list[UserRatedGame]:
    with Session() as session:
        ratings = (
            session.query(UserRatingDB)
            .options(joinedload(UserRatingDB.game_rel).joinedload(Game.platforms))
            .filter(UserRatingDB.user_id == user_id)
            .all()
        )
        return [
            UserRatedGame(
                game_id=r.game_rel.id,
                game_name=r.game_rel.name,
                cover_url=r.game_rel.url,
                rating=r.rating,
                platforms=[p.name for p in r.game_rel.platforms],
            )
            for r in ratings
        ]


#Add a rating 
@router.post("/rate_game/")
def rate_game(
    body: RateGameRequest,
    user_id: UUID = Depends(get_current_user),
):
    with Session() as session:
        rating_db_row = session.get(UserRatingDB, (user_id, body.game_id))
        if rating_db_row is not None:
            rating_db_row.rating = body.rating
        else:
            rating_db_row = UserRatingDB(
                user_id=user_id, game_id=body.game_id, rating=body.rating
            )
            session.add(rating_db_row)
        session.commit()

    return {"game_id": body.game_id, "rating": body.rating}


#Delete a rating
@router.delete("/delete_rating/{game_id}")
def delete_rating(
    game_id: int,
    user_id: UUID = Depends(get_current_user),
):
    with Session() as session:
        rating_db_row = session.get(UserRatingDB, (user_id, game_id))
        if rating_db_row is None:
            raise HTTPException(
                status_code=404, detail="Trying to delete rating that doesn't exist"
            )
        session.delete(rating_db_row)
        session.commit()

    return {"game_id": game_id}
