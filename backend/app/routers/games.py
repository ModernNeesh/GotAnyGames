from fastapi import APIRouter, HTTPException
from app.models.schemas import SearchbarGameData, FullGameData
from app.models.db import Game, MultiplayerMode, Platform
from app.database import Session
import sqlalchemy as sa
from sqlalchemy.orm import joinedload
import re

router = APIRouter(tags=["games"])


#Search for a given game
@router.get("/search_game/{query}")
def search_games(query: str, limit: int | None = 5) -> list[SearchbarGameData]:
    with Session() as session:

        #Remove whitespace and special characters from query and check it against other game names cleaned the same way
        clean_query = re.sub(r'[^a-zA-Z0-9]', '', query)
        game_search_results = session.query(Game).options(joinedload(Game.platforms)).filter(Game.slug.ilike(f"%{clean_query}%")).all()

        #Separate results that belong to main games from those that belong to other kinds of versions (Bundles, Updates, etc.)
        main_game_results = []
        additional_game_results = []

        for game in game_search_results:
            platforms = [platform.name for platform in game.platforms]

            game_data = SearchbarGameData(
                id=game.id,
                name=game.name,
                total_rating=game.total_rating,
                total_rating_count=game.total_rating_count,
                cover_url=game.url,
                platforms=platforms
            )
            if game.game_type == 0:
                main_game_results.append(game_data)
            else:
                additional_game_results.append(game_data)

    num_main_results = len(main_game_results)

    #Only show non-main-games if there were fewer main game results than the limit
    if num_main_results < limit:
            num_additional_needed = limit - num_main_results
            final_search_results = main_game_results + additional_game_results[:num_additional_needed]
    else:
        final_search_results = main_game_results[:limit]

    return final_search_results


#Get full data of a given game
@router.get("/full_game_data/{game_id}")
def get_full_game_data(game_id: int) -> list[FullGameData]:
    with Session() as session:
        game = (session.query(Game)
                .options(joinedload(Game.platforms), joinedload(Game.genres), joinedload(Game.game_modes), joinedload(Game.multiplayer_modes))
                .filter(Game.id == game_id).first())

        if not game:
           raise HTTPException(status_code=404, detail="Game not found")

        #Aggregate multiplayer modes so that they are grouped by their features
        modes = (session.query(
            MultiplayerMode.dropin,
            MultiplayerMode.campaigncoop,
            MultiplayerMode.offlinecoopmax,
            MultiplayerMode.offlinepvpmax,
            MultiplayerMode.onlinecoopmax,
            MultiplayerMode.onlinepvpmax,
            MultiplayerMode.splitscreen,
            sa.func.array_agg(sa.distinct(MultiplayerMode.platform)).label('platforms'))
             .filter(MultiplayerMode.game == game_id)
             .group_by(
                MultiplayerMode.dropin,
                MultiplayerMode.campaigncoop,
                MultiplayerMode.offlinecoopmax,
                MultiplayerMode.offlinepvpmax,
                MultiplayerMode.onlinecoopmax,
                MultiplayerMode.onlinepvpmax,
                MultiplayerMode.splitscreen)
             .all())

        return_data = []

        #Each row is a different multiplayer mode (platform-agnostic)
        for mode in modes:
            this_data = FullGameData(
                id=game.id,
                name=game.name,
                total_rating=game.total_rating,
                total_rating_count=game.total_rating_count,
                summary=game.summary,
                cover_url=game.url,

                dropin=mode.dropin,
                campaigncoop=mode.campaigncoop,
                offlinecoopmax=mode.offlinecoopmax,
                offlinepvpmax=mode.offlinepvpmax,
                onlinecoopmax=mode.onlinecoopmax,
                onlinepvpmax=mode.onlinepvpmax,
                splitscreen=mode.splitscreen,
                platforms=[session.query(Platform.name).filter(Platform.id == platform_id).scalar() for platform_id in mode.platforms],

                genres=[genre.name for genre in game.genres],
                game_modes=[game_mode.name for game_mode in game.game_modes]
            )
            return_data.append(this_data)

    return return_data
