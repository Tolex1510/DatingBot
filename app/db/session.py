from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

async_engine = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db(database_url: str) -> None:
    global async_engine, async_session_factory
    async_engine = create_async_engine(database_url, echo=False)
    async_session_factory = async_sessionmaker(
        async_engine, expire_on_commit=False
    )


async def close_db() -> None:
    global async_engine
    if async_engine:
        await async_engine.dispose()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if async_session_factory is None:
        raise RuntimeError("Database not initialized")
    async with async_session_factory() as session:
        yield session
