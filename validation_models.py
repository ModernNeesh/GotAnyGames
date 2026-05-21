from pydantic import BaseModel, ConfigDict, HttpUrl, Field, model_validator

# DATA GOING OUT

#Data that user sees in a dropdown menu when they search for a game
class SearchbarGameData(BaseModel):
    id: int = Field(default=None, gt = 0)
    name: str = Field(default=None, min_length=1)
    total_rating: float
    total_rating_count: int
    cover_url: HttpUrl
    platforms: list[str]

    model_config = ConfigDict(from_attributes=True)


#Game data that goes to the frontend, to be displayed when more detailed info is needed
class FullGameData(BaseModel):
    #Columns from Games table
    id: int = Field(default=None, gt = 0)
    name: str = Field(default=None, min_length=1)
    total_rating: float
    total_rating_count: int
    summary: str
    cover_url: HttpUrl
    
    #Columns joined from Multiplayer Modes table
    dropin: bool
    campaigncoop: bool
    offlinecoopmax: int = Field(default=None, gt = 0)
    offlinepvpmax: int = Field(default=None, gt = 0)
    onlinecoopmax: int = Field(default=None, gt = 0)
    onlinepvpmax: int = Field(default=None, gt = 0)
    splitscreen: bool
    platforms: list[str]

    #Columns from other feature tables
    genres: list[str]
    game_modes: list[str]
    

    model_config = ConfigDict(from_attributes=True)


# DATA COMING IN

#User data (received when user creates an account)
class UserModel(BaseModel):
    name: str = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="forbid")

class UserResponseModel(BaseModel):
    id: int = Field(default=None, gt=0)
    name: str = Field(default=None, min_length=1)

    model_config = ConfigDict(from_attributes=True)

class UserPrefModel(BaseModel):
    user_id: int = Field(default=None, gt = 0)
    platform_id: list[int]
    online: list[bool]
    offline: list[bool]


    #The lists should be of the same length
    @model_validator(mode='after')
    def check_lengths(self) -> UserPrefModel:
        if not (len(self.platform_id) == len(self.online) == len(self.offline)):
            raise ValueError("User should have preferences for online or offline play for each platform")
        return self



#Rating data (received when user creates a rating)
class RatingModel(BaseModel):
    user_id: int = Field(default=None, gt = 0)
    game_id: int = Field(default=None, gt = 0)
    rating: int = Field(default=None, ge = 0, le = 100)



#Group data (received when a group is created, renamed, or someone is added)
class GroupModel(BaseModel):
    name: str = Field(default=None, min_length=1)
    user_id: int = Field(default=None, gt = 0)

    model_config = ConfigDict(extra="forbid")

class GroupResponseModel(BaseModel):
    id: int = Field(default=None, gt=0)
    name: str = Field(default=None, min_length=1)

    model_config = ConfigDict(from_attributes=True)






