import uuid

from app.db.redis import get_redis

BROWSE_QUEUE_KEY = "browse:{user_id}"
BROWSE_QUEUE_TTL = 3600  # 1 hour


async def pop_next_profile(user_id: uuid.UUID) -> str | None:
    redis = get_redis()
    key = BROWSE_QUEUE_KEY.format(user_id=user_id)
    return await redis.lpop(key)


async def cache_profiles(user_id: uuid.UUID, profile_user_ids: list[str]) -> None:
    redis = get_redis()
    key = BROWSE_QUEUE_KEY.format(user_id=user_id)
    pipe = redis.pipeline()
    pipe.delete(key)
    if profile_user_ids:
        pipe.rpush(key, *profile_user_ids)
        pipe.expire(key, BROWSE_QUEUE_TTL)
    await pipe.execute()


async def get_remaining_count(user_id: uuid.UUID) -> int:
    redis = get_redis()
    key = BROWSE_QUEUE_KEY.format(user_id=user_id)
    return await redis.llen(key)


async def invalidate_browse_cache(user_id: uuid.UUID) -> None:
    redis = get_redis()
    key = BROWSE_QUEUE_KEY.format(user_id=user_id)
    await redis.delete(key)


async def invalidate_all_browse_caches() -> None:
    redis = get_redis()
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match="browse:*", count=100)
        if keys:
            await redis.delete(*keys)
        if cursor == 0:
            break
