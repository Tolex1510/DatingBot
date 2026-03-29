import redis.asyncio as aioredis

redis_client: aioredis.Redis | None = None


async def init_redis(redis_url: str) -> None:
    global redis_client
    redis_client = aioredis.from_url(redis_url, decode_responses=True)


async def close_redis() -> None:
    global redis_client
    if redis_client:
        await redis_client.close()


def get_redis() -> aioredis.Redis:
    if redis_client is None:
        raise RuntimeError("Redis not initialized")
    return redis_client
