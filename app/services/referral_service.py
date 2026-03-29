import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import referral_repo
from app.models.referral import Referral
from app.services import rating_service


async def create_referral(
    session: AsyncSession, referrer_id: uuid.UUID, referred_id: uuid.UUID
) -> Referral | None:
    if referrer_id == referred_id:
        return None
    if await referral_repo.exists_for_referred(session, referred_id):
        return None

    referral = await referral_repo.create(session, referrer_id, referred_id)
    # Recalculate referrer's combined rating (bonus changed)
    await rating_service.calculate_combined_rating(session, referrer_id)
    return referral


async def get_referral_count(session: AsyncSession, referrer_id: uuid.UUID) -> int:
    return await referral_repo.count_by_referrer(session, referrer_id)
