import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.referral import Referral


async def create(
    session: AsyncSession, referrer_id: uuid.UUID, referred_id: uuid.UUID
) -> Referral:
    referral = Referral(referrer_id=referrer_id, referred_id=referred_id)
    session.add(referral)
    await session.flush()
    return referral


async def count_by_referrer(session: AsyncSession, referrer_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(Referral).where(
        Referral.referrer_id == referrer_id
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def exists_for_referred(session: AsyncSession, referred_id: uuid.UUID) -> bool:
    stmt = select(Referral).where(Referral.referred_id == referred_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None
