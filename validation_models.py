from pydantic import BaseModel, ConfigDict


#Feature base models
class Game(BaseModel):
    id: int
    name: str
    total_rating: float
    total_rating_count: int
    summary: str
    cover_url: str
    dropin: bool
    campaigncoop: bool
    offlinecoopmax: int
    offlinemax: int
    onlinecoopmax: int
    onlinemax: int
    platform: int
    splitscreen: bool
    model_config = ConfigDict(from_attributes=True)





