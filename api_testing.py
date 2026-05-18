from fastapi import FastAPI
from validation_models import SearchbarGameData
from db_models import Game, init_db
import sqlalchemy as sa
from sqlalchemy.orm import joinedload
import re

app = FastAPI()

engine, Base, Session = init_db()

#Request to search the games table; returns games formatted for dropdown menu in frontend
@app.get("/searchgame/{query}")
def search_games(query: str, limit: int = 5) -> list[SearchbarGameData]:
    with Session() as session:

        clean_query = re.sub(r'[^a-zA-Z0-9]', '', query)

        game_search_results = session.query(Game).options(joinedload(Game.platforms)).filter(Game.slug.ilike(f"%{clean_query}%")).all()

        #Join search results and Multiplayer Modes tables to get all relevant data (formatted as a SearchbarGameData model)
        main_game_results = []
        additional_game_results = []
        
        for game in game_search_results:
            # Collect all platform names for this game
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

    if num_main_results < limit:
        num_additional_needed = limit - num_main_results
        final_search_results = main_game_results + additional_game_results[:num_additional_needed]

    else:
        final_search_results = main_game_results[:limit]

    return final_search_results



