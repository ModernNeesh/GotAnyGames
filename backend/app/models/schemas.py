from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, ConfigDict, HttpUrl, Field, model_validator

# DATA GOING OUT

class SearchbarGameData(BaseModel):
    id: int = Field(default=None, gt = 0)
    name: str = Field(default=None, min_length=1)
    total_rating: float
    total_rating_count: int
    cover_url: HttpUrl
    platforms: list[str]

    model_config = ConfigDict(from_attributes=True)


class FullGameData(BaseModel):
    id: int = Field(default=None, gt = 0)
    name: str = Field(default=None, min_length=1)
    total_rating: float
    total_rating_count: int
    summary: str
    cover_url: HttpUrl

    dropin: bool
    campaigncoop: bool
    offlinecoopmax: int = Field(default=None, ge = 0)
    offlinepvpmax: int = Field(default=None, ge = 0)
    onlinecoopmax: int = Field(default=None, ge = 0)
    onlinepvpmax: int = Field(default=None, ge = 0)
    splitscreen: bool
    platforms: list[str]

    genres: list[str]
    game_modes: list[str]

    model_config = ConfigDict(from_attributes=True)


class AuthSyncResponse(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserRatedGame(BaseModel):
    game_id: int
    game_name: str
    cover_url: HttpUrl
    rating: int
    platforms: list[str]

    model_config = ConfigDict(from_attributes=True)


# DATA COMING IN (auth-protected — user_id derived from JWT)

class ExistingUserModel(BaseModel):
    id: UUID
    name: str = Field(default=None, min_length=1)

    model_config = ConfigDict(from_attributes=True)


class RenameRequest(BaseModel):
    name: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class UserPrefRequest(BaseModel):
    platform_id: list[int]
    online: list[bool]
    offline: list[bool]

    @model_validator(mode='after')
    def check_lengths(self) -> UserPrefRequest:
        if not (len(self.platform_id) == len(self.online) == len(self.offline)):
            raise ValueError("User should have preferences for online or offline play for each platform")
        return self

    model_config = ConfigDict(extra="forbid")


class RateGameRequest(BaseModel):
    game_id: int = Field(gt=0)
    rating: int = Field(ge=0, le=100)

    model_config = ConfigDict(extra="forbid")


class ExistingGroupModel(BaseModel):
    id: int = Field(default=None, gt=0)
    name: str = Field(default=None, min_length=1)

    model_config = ConfigDict(from_attributes=True)


class CreateGroupRequest(BaseModel):
    name: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class GroupIdRequest(BaseModel):
    group_id: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")


class RenameGroupRequest(BaseModel):
    id: int = Field(gt=0)
    name: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")
