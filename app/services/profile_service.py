import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import profile_repo, user_repo
from app.models.profile import Profile
from app.services import rating_service


async def create_profile(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str | None,
    age: int,
    gender: str,
    city: str,
    country: str | None = None,
    bio: str | None = None,
    interests: list | None = None,
    preferences: dict | None = None,
) -> Profile:
    user = await user_repo.get_by_id(session, user_id)
    if not user:
        raise ValueError("User not found")

    existing = await profile_repo.get_by_user_id(session, user_id)
    if existing:
        raise ValueError("Profile already exists")

    data = {
        "name": name,
        "age": age,
        "gender": gender,
        "city": city,
        "country": country,
        "bio": bio,
        "interests": interests,
        "preferences": preferences,
    }
    profile = await profile_repo.create(session, user_id, data)
    await rating_service.recalculate_full(session, user_id)
    return profile


async def get_profile(
    session: AsyncSession, user_id: uuid.UUID
) -> Profile | None:
    return await profile_repo.get_by_user_id(session, user_id)


async def get_profile_by_id(
    session: AsyncSession, profile_id: uuid.UUID
) -> Profile | None:
    return await profile_repo.get_by_id(session, profile_id)


async def update_profile(
    session: AsyncSession, profile_id: uuid.UUID, **kwargs
) -> Profile | None:
    profile = await profile_repo.get_by_id(session, profile_id)
    if not profile:
        return None
    updated = await profile_repo.update(session, profile, kwargs)

    # Publish event — consumer recalculates rating asynchronously
    from app.events.publisher import publish
    await publish("profile.updated", {"user_id": str(profile.user_id)})

    return updated


async def delete_profile(
    session: AsyncSession, profile_id: uuid.UUID
) -> None:
    await profile_repo.delete(session, profile_id)


async def list_profiles(
    session: AsyncSession,
    limit: int = 10,
    offset: int = 0,
    gender: str | None = None,
    city: str | None = None,
) -> list[Profile]:
    return await profile_repo.list_profiles(session, limit, offset, gender, city)
