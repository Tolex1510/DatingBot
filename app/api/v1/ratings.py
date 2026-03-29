import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import RatingResponse
from app.services import rating_service

router = APIRouter(prefix="/rating", tags=["rating"])


@router.get("/{user_id}", response_model=RatingResponse)
async def get_rating(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    rating = await rating_service.get_rating(session, user_id)
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    return RatingResponse.model_validate(rating)


@router.post("/{user_id}/recalculate", response_model=RatingResponse)
async def recalculate_rating(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await rating_service.recalculate_full(session, user_id)
    rating = await rating_service.get_rating(session, user_id)
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    return RatingResponse.model_validate(rating)
