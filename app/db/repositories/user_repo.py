import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.user import TgUser


async def get_by_tg_id(session: AsyncSession, tg_id: int) -> TgUser | None:
    stmt = (
        select(TgUser)
        .options(joinedload(TgUser.profile))
        .where(TgUser.tg_id == tg_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> TgUser | None:
    stmt = (
        select(TgUser)
        .options(joinedload(TgUser.profile))
        .where(TgUser.id == user_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create(
    session: AsyncSession,
    tg_id: int,
    username: str | None,
    first_name: str,
    last_name: str | None,
) -> TgUser:
    user = TgUser(
        tg_id=tg_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
    )
    session.add(user)
    await session.flush()
    return user


async def update_last_seen(session: AsyncSession, user_id: uuid.UUID) -> None:
    stmt = update(TgUser).where(TgUser.id == user_id).values(last_seen=func.now())
    await session.execute(stmt)
