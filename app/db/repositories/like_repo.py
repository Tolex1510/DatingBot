import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.like import Like


async def create(
    session: AsyncSession,
    liker_id: uuid.UUID,
    liked_id: uuid.UUID,
    is_like: bool = True,
) -> Like:
    like = Like(liker_id=liker_id, liked_id=liked_id, is_like=is_like)
    session.add(like)
    await session.flush()
    return like


async def exists(
    session: AsyncSession, liker_id: uuid.UUID, liked_id: uuid.UUID
) -> bool:
    stmt = select(Like).where(
        and_(Like.liker_id == liker_id, Like.liked_id == liked_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def check_mutual(
    session: AsyncSession, user_a: uuid.UUID, user_b: uuid.UUID
) -> bool:
    stmt = select(Like).where(
        and_(Like.liker_id == user_b, Like.liked_id == user_a, Like.is_like == True)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None
