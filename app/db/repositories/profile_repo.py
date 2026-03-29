import uuid

from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.like import Like
from app.models.profile import Profile


async def create(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: dict,
) -> Profile:
    profile = Profile(user_id=user_id, **data)
    session.add(profile)
    await session.flush()
    return profile


async def get_by_user_id(
    session: AsyncSession, user_id: uuid.UUID
) -> Profile | None:
    stmt = select(Profile).where(Profile.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_id(
    session: AsyncSession, profile_id: uuid.UUID
) -> Profile | None:
    stmt = select(Profile).where(Profile.id == profile_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update(
    session: AsyncSession,
    profile: Profile,
    data: dict,
) -> Profile:
    for key, value in data.items():
        if value is not None:
            setattr(profile, key, value)
    await session.flush()
    return profile


async def delete(session: AsyncSession, profile_id: uuid.UUID) -> None:
    stmt = sa_delete(Profile).where(Profile.id == profile_id)
    await session.execute(stmt)


async def list_profiles(
    session: AsyncSession,
    limit: int = 10,
    offset: int = 0,
    gender: str | None = None,
    city: str | None = None,
) -> list[Profile]:
    stmt = select(Profile)
    if gender:
        stmt = stmt.where(Profile.gender == gender)
    if city:
        stmt = stmt.where(Profile.city == city)
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_next_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> Profile | None:
    """Get next unseen profile for the user."""
    seen_subq = select(Like.liked_id).where(Like.liker_id == user_id)
    stmt = (
        select(Profile)
        .where(
            Profile.user_id != user_id,
            Profile.user_id.notin_(seen_subq),
            Profile.is_active == True,
        )
        .order_by(Profile.created_at)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
