import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.bot.main import create_bot_app
from app.config import settings
from app.db.redis import close_redis, init_redis
from app.db.session import close_db, init_db
from app.events.publisher import close_publisher, init_publisher
from app.events.consumer import start_consumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def start_bot_with_retry(bot_token: str, max_retries: int = 5):
    for attempt in range(1, max_retries + 1):
        try:
            bot_app = create_bot_app(bot_token)
            await bot_app.initialize()
            await bot_app.start()
            await bot_app.updater.start_polling()
            logger.info("Telegram bot started")
            return bot_app
        except Exception as e:
            logger.warning(
                "Bot start attempt %d/%d failed: %s", attempt, max_retries, e
            )
            if attempt < max_retries:
                await asyncio.sleep(5)
    logger.error("Failed to start bot after %d attempts", max_retries)
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")

    await init_db(settings.database_url)
    logger.info("Database initialized")

    await init_redis(settings.REDIS_URL)
    logger.info("Redis initialized")

    # RabbitMQ event bus
    consumer_task = None
    try:
        await init_publisher()
        consumer_task = await start_consumer()
        logger.info("RabbitMQ event bus started")
    except Exception as e:
        logger.warning("RabbitMQ init failed (events disabled): %s", e)

    from app.services.s3_service import ensure_bucket
    try:
        await ensure_bucket()
        logger.info("S3 bucket ready")
    except Exception as e:
        logger.warning("S3 bucket init failed: %s", e)

    bot_app = None
    if settings.BOT_TOKEN:
        bot_app = await start_bot_with_retry(settings.BOT_TOKEN)
    else:
        logger.warning("BOT_TOKEN not set, bot not started")

    yield

    if bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
        logger.info("Telegram bot stopped")

    if consumer_task:
        consumer_task.cancel()
    await close_publisher()
    await close_redis()
    await close_db()
    logger.info("Application stopped")


app = FastAPI(
    title="Dating Bot API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(v1_router)
