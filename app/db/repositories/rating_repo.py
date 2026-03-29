import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.like import Like
from app.models.profile import Profile
from app.models.rating import Rating


async def get_by_user_id(session: AsyncSession, user_id: uuid.UUID) -> Rating | None:
    stmt = select(Rating).where(Rating.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create(session: AsyncSession, user_id: uuid.UUID) -> Rating:
    rating = Rating(user_id=user_id)
    session.add(rating)
    await session.flush()
    return rating


async def update(session: AsyncSession, rating: Rating, data: dict) -> Rating:
    for key, value in data.items():
        setattr(rating, key, value)
    await session.flush()
    return rating


async def get_top_rated_profiles(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 20,
) -> list[uuid.UUID]:
    """Get top-rated unseen active profile user_ids for a user."""
    seen_subq = select(Like.liked_id).where(Like.liker_id == user_id)
    stmt = (
        select(Profile.user_id)
        .outerjoin(Rating, Rating.user_id == Profile.user_id)
        .where(
            Profile.user_id != user_id,
            Profile.user_id.notin_(seen_subq),
            Profile.is_active == True,
        )
        .order_by(Rating.final_rating.desc().nulls_last())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]
