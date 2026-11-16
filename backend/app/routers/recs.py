from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session as SessionType

from app.auth import get_current_user
from app.database import Session
from app.group_preferences import summarize_group_preferences
from app.models.db import Game, MultiplayerMode, Platform, UserRating, group_membership
from app.models.schemas import GroupRecommendationsModel
from app.routers.games import pull_game_data
from app.routers.groups import require_group_member


router = APIRouter(tags=["recs"])


def get_recommendations_for_group(
    session: SessionType, group_id: int, num_games: int = 1,
) -> tuple[int, list[int], list[float]]:
    """
    Get recommendations for a group.

    Currently, a game can only be recommended if it:
        - Has been played and rated by all members
        - Is on a platform preferred by all members
        - Supports the proper play mode on that platform
    """

    #Get group preference summaries
    group_preferences = summarize_group_preferences(session, group_id)
    best_platforms_summaries = sorted(
        group_preferences.platforms,
        key=lambda platform: (
            -platform.member_percentage,
            -max(platform.offline_percentage, platform.online_percentage),
            platform.platform_id,
        ),
    )[:3]
    if not best_platforms_summaries:
        return group_id, [], []

    #Select this group's favorite platforms and preferences for each one
    best_platforms = [platform.platform_id for platform in best_platforms_summaries]
    online_or_offline = {
        platform.platform_id: (
            "online" if platform.online_percentage >= platform.offline_percentage else "offline"
        )
        for platform in best_platforms_summaries
    }

    #This group's members and member count
    group_members = (
        select(group_membership.c.user_id)
        .where(group_membership.c.group_id == group_id)
        .correlate(None)
    )
    member_count = (
        select(func.count())
        .select_from(group_members)
        .correlate(None)
        .scalar_subquery()
    )

    #-----THIS NEEDS TO BE CHANGED WHEN AN ACTUAL RECOMMENDATION ALGORITHM IS IMPLEMENTED-----------
    # Get id and average rating of games rated by all members
    rated_by_members = (
        select(UserRating.game_id, func.avg(UserRating.rating).label("rating"))
        .where(UserRating.user_id.in_(group_members))
        .group_by(UserRating.game_id)
        .having(func.count(func.distinct(UserRating.user_id)) == member_count)
        .subquery()
    )

    #Get the subset of the above games that support the group's preferred platforms
    on_best_platforms = (
        select(Game.id.label("game_id"), rated_by_members.c.rating)
        .join(rated_by_members, Game.id == rated_by_members.c.game_id)
        .where(Game.platforms.any(Platform.id.in_(best_platforms)))
        .subquery()
    )


    #Get the subset of the above games that support the group's preferred play mode on each platform
    preferred_play_mode_filters = [
        and_(
            MultiplayerMode.platform == platform_id,
            or_(MultiplayerMode.onlinepvpmax > 1, MultiplayerMode.onlinecoopmax > 1)
            if play_mode == "online"
            else or_(MultiplayerMode.offlinepvpmax > 1, MultiplayerMode.offlinecoopmax > 1),
        )
        for platform_id, play_mode in online_or_offline.items()
    ]
    supports_preferred_play_mode = (
        select(on_best_platforms.c.game_id, on_best_platforms.c.rating)
        .where(
            select(MultiplayerMode.id)
            .where(
                MultiplayerMode.game == on_best_platforms.c.game_id,
                or_(*preferred_play_mode_filters),
            )
            .exists()
        )
        .subquery()
    )

    #-----THIS NEEDS TO BE CHANGED WHEN AN ACTUAL RECOMMENDATION ALGORITHM IS IMPLEMENTED-----------
    #Get the highest rated games that fit all of the above criteria
    highest_rated_games = session.execute(
        select(supports_preferred_play_mode.c.game_id, supports_preferred_play_mode.c.rating)
        .order_by(desc(supports_preferred_play_mode.c.rating), supports_preferred_play_mode.c.game_id)
        .limit(num_games)
    ).all()

    return (
        group_id,
        [game_id for game_id, _ in highest_rated_games],
        [float(rating) for _, rating in highest_rated_games],
    )


@router.get("/get_recs/{group_id}")
def get_recs(
    group_id: int, user_id: UUID = Depends(get_current_user),
) -> GroupRecommendationsModel:
    with Session() as session:
        require_group_member(session, group_id, user_id)
        _, games, avg_ratings = get_recommendations_for_group(session, group_id)

        games_data_full = []
        ratings = []
        for game_id, rating in zip(games, avg_ratings):
            modes = pull_game_data(session=session, game_id=game_id)
            games_data_full.extend(modes)
            # Full game data has one row per mode.
            ratings.extend([rating] * len(modes))

    return GroupRecommendationsModel(group_id=group_id, games=games_data_full, ratings=ratings)
