from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, ConfigDict, HttpUrl, Field, model_validator

# DATA GOING OUT

#Data that shows up in the search bar for a game
class SearchbarGameData(BaseModel):
    id: int = Field(default=None, gt = 0)
    name: str = Field(default=None, min_length=1)
    total_rating: float
    total_rating_count: int
    cover_url: HttpUrl
    platforms: list[str]

    model_config = ConfigDict(from_attributes=True)


#Data that shows up when the user wants more info on a game
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


#Response from authentication function that checks if user exists in table.
class AuthSyncResponse(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)

#Data that shows on a user's rated games page.
class UserRatedGame(BaseModel):
    game_id: int
    game_name: str
    cover_url: HttpUrl
    rating: int
    platforms: list[str]

    model_config = ConfigDict(from_attributes=True)


#Data for an existing user.
class ExistingUserModel(BaseModel):
    id: UUID
    name: str = Field(default=None, min_length=1)

    model_config = ConfigDict(from_attributes=True)

#Data for an existing group.
class ExistingGroupModel(BaseModel):
    id: int = Field(default=None, gt=0)
    name: str = Field(default=None, min_length=1)

    model_config = ConfigDict(from_attributes=True)

#Detailed information about a group, including its members.
class GroupDetailModel(ExistingGroupModel):
    members: list[ExistingUserModel]


#An existing catalog platform available in the group preferences picker.
class GroupPlatformModel(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

#Play modes selected for one platform in a group.
class GroupPlatformPreferenceModel(BaseModel):
    platform_id: int = Field(gt=0, strict=True)
    online: bool = Field(strict=True)
    offline: bool = Field(strict=True)

    @model_validator(mode="after")
    def check_play_modes(self) -> GroupPlatformPreferenceModel:
        if not self.online and not self.offline:
            raise ValueError("Choose online or offline play for each platform")
        return self

    model_config = ConfigDict(extra="forbid", from_attributes=True)


#One member's platform-specific selections in a group.
class GroupPreferencesModel(BaseModel):
    platforms: list[GroupPlatformPreferenceModel]


#Counts and percentages for one platform selected by current group members.
class GroupPlatformPreferenceSummaryModel(BaseModel):
    platform_id: int
    platform_name: str
    member_count: int
    member_percentage: float
    online_count: int
    online_percentage: float
    offline_count: int
    offline_percentage: float


class GroupPreferenceSummaryModel(BaseModel):
    member_count: int
    platforms: list[GroupPlatformPreferenceSummaryModel]



# DATA COMING IN (auth-protected — user_id derived from JWT)


# Data that goes in when a user is trying to change their name
class RenameRequest(BaseModel):

    name: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

#Data that goes in when a user is trying to change their preferences.
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

#Data that goes in when a user is trying to rate a game.
class RateGameRequest(BaseModel):
    game_id: int = Field(gt=0)
    rating: int = Field(ge=0, le=100)

    model_config = ConfigDict(extra="forbid")

#Data that goes in when a user is trying to create a group.
class CreateGroupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# Data to identify a specific group by its ID.
class GroupIdRequest(BaseModel):
    group_id: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")

#Data to rename an existing group.
class RenameGroupRequest(CreateGroupRequest):
    id: int = Field(gt=0)


#The UUID of the user to add.
class AddGroupMemberRequest(BaseModel):

    user_id: UUID

    model_config = ConfigDict(extra="forbid")


# A complete replacement of the caller's preferences in a single group.
class GroupPreferencesRequest(BaseModel):
    platforms: list[GroupPlatformPreferenceModel] = Field(min_length=1)

    @model_validator(mode="after")
    def check_preferences(self) -> GroupPreferencesRequest:
        platform_ids = [platform.platform_id for platform in self.platforms]
        if len(platform_ids) != len(set(platform_ids)):
            raise ValueError("Choose each platform only once")
        return self

    model_config = ConfigDict(extra="forbid")
