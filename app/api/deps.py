from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session as db_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if db_session.async_session_factory is None:
        raise RuntimeError("Database not initialized")
    async with db_session.async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
