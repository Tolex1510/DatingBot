import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.profile import Profile
from app.services import rating_service

logger = logging.getLogger(__name__)

# Celery tasks run in a sync context, so we need a helper to run async code
_engine = None
_session_factory = None


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory
    if _session_factory is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


def _run_async(coro):
    """Run an async function from sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Import celery_app here to avoid circular imports
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.hourly_rating_update")
def hourly_rating_update():
    """Recalculate behavioral + combined ratings for all users with profiles."""
    logger.info("Starting hourly behavioral rating update")
    _run_async(_hourly_update())
    logger.info("Hourly rating update completed")


async def _hourly_update():
    factory = _get_session_factory()
    async with factory() as session:
        stmt = select(Profile.user_id).where(Profile.is_active == True)
        result = await session.execute(stmt)
        user_ids = [row[0] for row in result.all()]

    for user_id in user_ids:
        async with factory() as session:
            try:
                await rating_service.calculate_behavioral_rating(session, user_id)
                await rating_service.calculate_combined_rating(session, user_id)
                await session.commit()
            except Exception as e:
                logger.error("Failed to update rating for %s: %s", user_id, e)


@celery_app.task(name="app.workers.tasks.daily_rating_update")
def daily_rating_update():
    """Full recalculation of all ratings."""
    logger.info("Starting daily full rating update")
    _run_async(_daily_update())
    logger.info("Daily rating update completed")


async def _daily_update():
    factory = _get_session_factory()
    async with factory() as session:
        stmt = select(Profile.user_id).where(Profile.is_active == True)
        result = await session.execute(stmt)
        user_ids = [row[0] for row in result.all()]

    for user_id in user_ids:
        async with factory() as session:
            try:
                await rating_service.recalculate_full(session, user_id)
                await session.commit()
            except Exception as e:
                logger.error("Failed to recalculate rating for %s: %s", user_id, e)


@celery_app.task(name="app.workers.tasks.weekly_rating_aggregation")
def weekly_rating_aggregation():
    """Weekly full recalculation + cache invalidation."""
    logger.info("Starting weekly rating aggregation")
    _run_async(_weekly_aggregation())
    logger.info("Weekly rating aggregation completed")


async def _weekly_aggregation():
    factory = _get_session_factory()

    # Full recalculate all users
    async with factory() as session:
        stmt = select(Profile.user_id).where(Profile.is_active == True)
        result = await session.execute(stmt)
        user_ids = [row[0] for row in result.all()]

    for user_id in user_ids:
        async with factory() as session:
            try:
                await rating_service.recalculate_full(session, user_id)
                await session.commit()
            except Exception as e:
                logger.error("Weekly recalc failed for %s: %s", user_id, e)

    # Invalidate all browse caches
    from app.services import cache_service
    from app.db.redis import init_redis
    from app.config import settings
    try:
        await init_redis(settings.REDIS_URL)
        await cache_service.invalidate_all_browse_caches()
    except Exception as e:
        logger.error("Cache invalidation failed: %s", e)


@celery_app.task(name="app.workers.tasks.recalculate_user_rating")
def recalculate_user_rating(user_id_str: str):
    """Recalculate a single user's rating (triggered by events)."""
    import uuid
    user_id = uuid.UUID(user_id_str)
    _run_async(_recalculate_single(user_id))


async def _recalculate_single(user_id):
    factory = _get_session_factory()
    async with factory() as session:
        await rating_service.recalculate_full(session, user_id)
        await session.commit()
