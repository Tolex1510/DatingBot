import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services import match_service, chat_service

router = APIRouter(prefix="/matches", tags=["matches"])


class MatchResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    matched_user_id: uuid.UUID
    chat_id: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[MatchResponse])
async def get_matches(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    matches = await match_service.get_matches(session, user_id)
    return [MatchResponse.model_validate(m) for m in matches]
