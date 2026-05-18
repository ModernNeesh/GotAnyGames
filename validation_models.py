from pydantic import BaseModel, ConfigDict


#Data that user sees in a dropdown menu when they search for a game
class SearchbarGameData(BaseModel):
    id: int
    name: str
    total_rating: float
    total_rating_count: int
    cover_url: str
    platforms: list[str]

    model_config = ConfigDict(from_attributes=True)


#Game data that goes to the frontend, to be displayed when more detailed info is needed
class FullGameData(BaseModel):
    #Columns from Games table
    id: int
    name: str
    total_rating: float
    total_rating_count: int
    summary: str
    cover_url: str
    
    #Columns joined from Multiplayer Modes table
    dropin: bool
    campaigncoop: bool
    offlinecoopmax: int
    offlinepvpmax: int
    onlinecoopmax: int
    onlinepvpmax: int
    platform: str
    splitscreen: bool

    model_config = ConfigDict(from_attributes=True)





