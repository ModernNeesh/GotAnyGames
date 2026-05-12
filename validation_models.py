from pydantic import BaseModel, ConfigDict


#Feature base models
class GenreBase(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class GameModeBase(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class PlatformBase(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)



