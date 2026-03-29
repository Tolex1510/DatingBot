import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import UserRegisterRequest, UserResponse, UserWithProfileResponse
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse)
async def register_user(
    body: UserRegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    user = await user_service.register_user(
        session,
        tg_id=body.telegram_id,
        username=body.username,
        first_name=body.first_name,
        last_name=body.last_name,
    )
    return UserResponse.from_model(user)


@router.get("/{user_id}", response_model=UserWithProfileResponse)
async def get_user(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    user = await user_service.get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserWithProfileResponse.from_model(user)
