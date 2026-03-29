from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.like import Like
from app.models.match import Match
from app.models.profile import Profile
from app.models.rating import Rating
from app.models.user import TgUser

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics(session: AsyncSession = Depends(get_db)):
    total_users = (await session.execute(
        select(func.count()).select_from(TgUser)
    )).scalar_one()

    active_profiles = (await session.execute(
        select(func.count()).select_from(Profile).where(Profile.is_active == True)
    )).scalar_one()

    total_matches = (await session.execute(
        select(func.count()).select_from(Match)
    )).scalar_one()

    total_likes = (await session.execute(
        select(func.count()).select_from(Like).where(Like.is_like == True)
    )).scalar_one()

    avg_rating = (await session.execute(
        select(func.avg(Rating.final_rating))
    )).scalar_one() or 0.0

    return {
        "total_users": total_users,
        "active_profiles": active_profiles,
        "total_matches": total_matches,
        "total_likes": total_likes,
        "avg_rating": round(float(avg_rating), 4),
    }
