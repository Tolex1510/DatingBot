import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- User ---

class UserRegisterRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str
    last_name: str | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    telegram_id: int
    username: str | None
    first_name: str
    last_name: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, user) -> "UserResponse":
        return cls(
            id=user.id,
            telegram_id=user.tg_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            created_at=user.created_at,
        )


# --- Profile ---

class ProfileCreateRequest(BaseModel):
    user_id: uuid.UUID
    name: str | None = None
    age: int = Field(ge=18, le=100)
    gender: str = Field(max_length=20)
    city: str = Field(max_length=100)
    country: str | None = None
    bio: str | None = None
    interests: list[str] | None = None
    preferences: dict | None = None


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    age: int | None = Field(default=None, ge=18, le=100)
    gender: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = None
    bio: str | None = None
    interests: list[str] | None = None
    preferences: dict | None = None


class ProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str | None
    age: int
    gender: str
    city: str
    country: str | None
    bio: str | None
    interests: list | None
    preferences: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RatingResponse(BaseModel):
    user_id: uuid.UUID
    primary_rating: float
    behavioral_rating: float
    final_rating: float
    age_score: float
    gender_score: float
    interests_score: float
    geo_score: float
    completeness_score: float
    photos_score: float
    likes_count_score: float
    like_dislike_ratio: float
    match_rate: float
    message_rate: float
    activity_time_score: float
    bonus_points: float

    model_config = ConfigDict(from_attributes=True)


class UserWithProfileResponse(UserResponse):
    profile: ProfileResponse | None = None

    @classmethod
    def from_model(cls, user) -> "UserWithProfileResponse":
        profile = None
        if user.profile:
            profile = ProfileResponse.model_validate(user.profile)
        return cls(
            id=user.id,
            telegram_id=user.tg_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            created_at=user.created_at,
            profile=profile,
        )
