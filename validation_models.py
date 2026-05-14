from pydantic import BaseModel, ConfigDict


#Game data that goes to the frontend, to be displayed in dropdowns and rated
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





