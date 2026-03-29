"""Event consumer — listens to domain events from RabbitMQ and processes them."""
import asyncio
import json
import logging
import uuid

import aio_pika

from app.config import settings

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "dating_events"
QUEUE_NAME = "dating_events_worker"


async def start_consumer() -> asyncio.Task:
    """Start consuming events in background. Returns the asyncio task."""
    task = asyncio.create_task(_consume())
    return task


async def _consume() -> None:
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
    )
    queue = await channel.declare_queue(QUEUE_NAME, durable=True)

    # Bind to all events we care about
    await queue.bind(exchange, routing_key="profile.liked")
    await queue.bind(exchange, routing_key="profile.skipped")
    await queue.bind(exchange, routing_key="match.created")
    await queue.bind(exchange, routing_key="profile.updated")
    await queue.bind(exchange, routing_key="profile.created")

    logger.info("RabbitMQ consumer started, listening on queue: %s", QUEUE_NAME)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                try:
                    await _handle_message(message)
                except Exception as e:
                    logger.error("Error handling event: %s", e)


async def _handle_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    routing_key = message.routing_key
    data = json.loads(message.body)
    logger.info("Received event: %s", routing_key)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.db import session as db_session

    factory = db_session.async_session_factory
    if not factory:
        logger.error("DB not initialized, cannot process event")
        return

    if routing_key in ("profile.liked", "profile.skipped"):
        await _handle_interaction(factory, data)
    elif routing_key == "match.created":
        await _handle_match(factory, data)
    elif routing_key in ("profile.updated", "profile.created"):
        await _handle_profile_change(factory, data)


async def _handle_interaction(factory, data: dict) -> None:
    """Recalculate behavioral + combined rating for the target user."""
    from app.services import rating_service

    target_user_id = uuid.UUID(data["target_user_id"])

    async with factory() as session:
        await rating_service.calculate_behavioral_rating(session, target_user_id)
        await rating_service.calculate_combined_rating(session, target_user_id)
        await session.commit()

    logger.info("Updated rating for user %s after interaction", target_user_id)


async def _handle_match(factory, data: dict) -> None:
    """Recalculate ratings for both users in a match."""
    from app.services import rating_service

    user_a = uuid.UUID(data["user_id"])
    user_b = uuid.UUID(data["matched_user_id"])

    for uid in (user_a, user_b):
        async with factory() as session:
            await rating_service.calculate_behavioral_rating(session, uid)
            await rating_service.calculate_combined_rating(session, uid)
            await session.commit()

    logger.info("Updated ratings for match: %s <-> %s", user_a, user_b)


async def _handle_profile_change(factory, data: dict) -> None:
    """Recalculate primary + combined rating and invalidate caches."""
    from app.services import rating_service, cache_service

    user_id = uuid.UUID(data["user_id"])

    async with factory() as session:
        await rating_service.calculate_primary_rating(session, user_id)
        await rating_service.calculate_combined_rating(session, user_id)
        await session.commit()

    await cache_service.invalidate_all_browse_caches()
    logger.info("Updated primary rating for user %s after profile change", user_id)
