"""Event publisher — sends domain events to RabbitMQ."""
import json
import logging

import aio_pika

from app.config import settings

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "dating_events"

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None
_exchange: aio_pika.abc.AbstractExchange | None = None


async def init_publisher() -> None:
    global _connection, _channel, _exchange
    _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    _channel = await _connection.channel()
    _exchange = await _channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
    )
    logger.info("RabbitMQ publisher initialized (exchange: %s)", EXCHANGE_NAME)


async def close_publisher() -> None:
    global _connection
    if _connection:
        await _connection.close()
        logger.info("RabbitMQ publisher closed")


async def publish(routing_key: str, data: dict) -> None:
    """Publish an event to the exchange.

    routing_key examples: profile.liked, match.created, profile.updated, rating.updated
    """
    if not _exchange:
        logger.warning("Publisher not initialized, skipping event: %s", routing_key)
        return

    body = json.dumps(data, default=str).encode()
    message = aio_pika.Message(
        body=body,
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )
    await _exchange.publish(message, routing_key=routing_key)
    logger.info("Published event: %s", routing_key)
