from fastapi import FastAPI
from app.routers import games, users, groups, ratings

app = FastAPI()

app.include_router(games.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(ratings.router)
