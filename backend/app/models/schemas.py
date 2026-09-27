from __future__ import annotations

from typing import Annotated
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


#Response from authentication function that checks if user exists in table
class AuthSyncResponse(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)

#Data that shows on a user's rated games page
class UserRatedGame(BaseModel):
    game_id: int
    game_name: str
    cover_url: HttpUrl
    rating: int
    platforms: list[str]

    model_config = ConfigDict(from_attributes=True)


#Data for an existing user
class ExistingUserModel(BaseModel):
    id: UUID
    name: str = Field(default=None, min_length=1)

    model_config = ConfigDict(from_attributes=True)


class ExistingGroupModel(BaseModel):
    id: int = Field(default=None, gt=0)
    name: str = Field(default=None, min_length=1)

    model_config = ConfigDict(from_attributes=True)


class GroupDetailModel(ExistingGroupModel):
    """Group ID/name plus member UUIDs and display names for the detail page."""

    members: list[ExistingUserModel]


class GroupPlatformModel(BaseModel):
    """An existing catalog platform available in the group preferences picker."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class GroupPreferencesModel(BaseModel):
    """One member's selection in a group; play modes apply to all platforms.

    The initial, unsaved response has no platforms and both modes false.
    Saving requires a nonempty selection through GroupPreferencesRequest.
    """

    platform_ids: list[int]
    online: bool
    offline: bool



# DATA COMING IN (auth-protected — user_id derived from JWT)


#Data that goes in when a user is trying to change their name
class RenameRequest(BaseModel):
    name: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


#Data that goes in when a user is trying to change their preferences
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


#Data that goes in when a user is trying to rate a game
class RateGameRequest(BaseModel):
    game_id: int = Field(gt=0)
    rating: int = Field(ge=0, le=100)

    model_config = ConfigDict(extra="forbid")


#Data that goes in when a user is trying to create a group
class CreateGroupRequest(BaseModel):
    """A trimmed 1-100 character name; the creator is identified by the JWT.

    Unexpected fields, including an attempted creator user_id, are rejected.
    """

    name: str = Field(min_length=1, max_length=100)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

#Data used to join or leave a group as the authenticated user
class GroupIdRequest(BaseModel):
    group_id: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")


class RenameGroupRequest(CreateGroupRequest):
    """Reuse creation's name validation and require a positive target group ID."""

    id: int = Field(gt=0)


class AddGroupMemberRequest(BaseModel):
    """The UUID of the existing user to add; caller identity comes from the JWT."""

    user_id: UUID

    model_config = ConfigDict(extra="forbid")


class GroupPreferencesRequest(BaseModel):
    """A complete replacement of the caller's preferences in a single group.

    Require real integer IDs (not booleans or numeric strings), no duplicates,
    and actual booleans with at least one play mode enabled. The router checks
    that platforms exist. No user_id is accepted, so callers edit only their
    own settings. Empty selections cannot be saved by this endpoint.
    """

    platform_ids: list[Annotated[int, Field(gt=0, strict=True)]] = Field(min_length=1)
    online: bool = Field(strict=True)
    offline: bool = Field(strict=True)

    @model_validator(mode="after")
    def check_preferences(self) -> GroupPreferencesRequest:
        """Reject duplicate platforms and a selection with no playable mode."""
        if len(self.platform_ids) != len(set(self.platform_ids)):
            raise ValueError("Choose each platform only once")
        if not self.online and not self.offline:
            raise ValueError("Choose online or offline play")
        return self

    model_config = ConfigDict(extra="forbid")
