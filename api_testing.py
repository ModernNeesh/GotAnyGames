from fastapi import FastAPI
from validation_models import FullGameData
from db_models import Game, MultiplayerMode, GameMode, Session
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, declarative_base

app = FastAPI()


example_search = "mar"

#Adding functionality to search the games table
with Session() as session:
    game_search_results = session.query(Game).filter(Game.name.ilike(f"%{example_search}%")).all()
    modes_search_results = session.query(MultiplayerMode).all()
    
    for search_result in modes_search_results[:5]:
        print(search_result, "\n")

#GET request: Enter a string, return data for all games with that string in it; ex: entering "mar" will return Mario games as well as Marvel games
