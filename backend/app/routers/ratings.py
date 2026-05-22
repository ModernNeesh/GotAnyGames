from fastapi import APIRouter, HTTPException
from validation_models import RatingModel
from db_models import UserRating as UserRatingDB
from database import Session

router = APIRouter(tags=["ratings"])


@router.post("/rate_game/")
def rate_game(user_rating: dict):
    rating_model = RatingModel.model_validate(user_rating)

    with Session() as session:
        rating_db_row = session.get(UserRatingDB, (rating_model.user_id, rating_model.game_id))
        if rating_db_row is not None:
            rating_db_row.rating = rating_model.rating
        else:
            rating_db_row = UserRatingDB(**rating_model.model_dump())
            session.add(rating_db_row)
        session.commit()

    return rating_model


@router.delete("/delete_rating/")
def delete_rating(user_rating: dict):
    rating_model = RatingModel.model_validate(user_rating)

    with Session() as session:
        rating_db_row = session.get(UserRatingDB, (rating_model.user_id, rating_model.game_id))
        if rating_db_row is not None:
            session.delete(rating_db_row)
        else:
            raise HTTPException(status_code=404, detail="Trying to delete rating that doesn't exist")
        session.commit()

    return rating_model
