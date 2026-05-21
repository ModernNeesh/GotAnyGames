from fastapi import FastAPI, HTTPException
from validation_models import *
from db_models import Game, MultiplayerMode, Platform, init_db, \
User as UserDB, UserPref as UserPrefDB, UserRating as UserRatingDB
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


#Request to get full data for a single game; returns that game formatted as a FullGameData model
@app.get("/getfullgamedata/{game_id}")
def get_full_game_data(game_id: int) -> list[FullGameData]:
    with Session() as session:
        #Get the game in question
        game = (session.query(Game)
                .options(joinedload(Game.platforms), joinedload(Game.genres), joinedload(Game.game_modes), joinedload(Game.multiplayer_modes))
                .filter(Game.id == game_id).first())

        if not game:
           raise HTTPException(status_code=404, detail="Game not found")

        #Get a list of platforms for each unique combination of the other multiplayer mode data.
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
        

        #Return the full data for the game, along with each of the multiplayer modes it supports
        return_data = []
        
        for mode in modes:
            this_data = FullGameData(
                #Data from Games table
                id=game.id,
                name=game.name,
                total_rating=game.total_rating,
                total_rating_count=game.total_rating_count,
                summary=game.summary,
                cover_url=game.url,

                #Data from MultiplayerModes table
                dropin=mode.dropin,
                campaigncoop=mode.campaigncoop,
                offlinecoopmax=mode.offlinecoopmax,
                offlinepvpmax=mode.offlinepvpmax,
                onlinecoopmax=mode.onlinecoopmax,
                onlinepvpmax=mode.onlinepvpmax,
                splitscreen=mode.splitscreen,
                platforms=[session.query(Platform.name).filter(Platform.id == platform_id).scalar() for platform_id in mode.platforms],

                #Data from other feature tables
                genres=[genre.name for genre in game.genres],
                game_modes=[game_mode.name for game_mode in game.game_modes]
            )
            return_data.append(this_data)

    return return_data


#POST/PUT/PATCH/DELETE requests - How does the user interact with the backend?
#1. Create a user account
#2. List their preferences (online or offline, platform, etc.)
#3. Create a new rating
#4. Update a rating
#5. Delete a rating
#6. Create a group
#7. Join a group
#8. Leave a group
#9. Rename a group
#10. Kick someone from a group


#1. Create a user account
@app.post("/createuser/")
def create_user(user: dict):
    user_model = UserModel.model_validate(user)

    with Session() as session:
        user_db_row = UserDB(**user_model.model_dump())
        session.add(user_db_row)
        session.commit()

   
    return user_model



#2. List user preferences
@app.post("/adduserprefs/")
def add_user_prefs(user_prefs: dict):
    prefs_model = UserPrefModel.model_validate(user_prefs)

    with Session() as session:
        prefs_db_row = UserPrefDB(**prefs_model.model_dump())
        session.add(prefs_db_row)
        session.commit()

    return prefs_model




#3. Create a new rating
@app.post("/rategame/")
def rate_game(user_rating: dict):
    rating_model = RatingModel.model_validate(user_rating)

    with Session() as session:
        rating_db_row = UserRatingDB(**rating_model.model_dump())
        session.add(rating_db_row)
        session.commit()

    return rating_model

