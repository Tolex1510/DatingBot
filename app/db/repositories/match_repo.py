import uuid

from sqlalchemy import or_, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match


async def create(
    session: AsyncSession, user_id: uuid.UUID, matched_user_id: uuid.UUID
) -> Match:
    match = Match(user_id=user_id, matched_user_id=matched_user_id)
    session.add(match)
    await session.flush()
    return match


async def exists(
    session: AsyncSession, user_a: uuid.UUID, user_b: uuid.UUID
) -> bool:
    stmt = select(Match).where(
        or_(
            and_(Match.user_id == user_a, Match.matched_user_id == user_b),
            and_(Match.user_id == user_b, Match.matched_user_id == user_a),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_user_matches(
    session: AsyncSession, user_id: uuid.UUID
) -> list[Match]:
    stmt = select(Match).where(
        or_(Match.user_id == user_id, Match.matched_user_id == user_id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
