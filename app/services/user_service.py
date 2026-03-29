import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import user_repo
from app.models.user import TgUser


async def register_user(
    session: AsyncSession,
    tg_id: int,
    username: str | None,
    first_name: str,
    last_name: str | None = None,
) -> TgUser:
    user = await user_repo.get_by_tg_id(session, tg_id)
    if user:
        return user
    return await user_repo.create(session, tg_id, username, first_name, last_name)


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> TgUser | None:
    return await user_repo.get_by_id(session, user_id)


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> TgUser | None:
    return await user_repo.get_by_tg_id(session, tg_id)
