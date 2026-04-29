"""
Write-Back (Write-Behind)

READ:  cache → miss → DB → populate cache
WRITE: cache only; background task flushes dirty keys to DB every FLUSH_INTERVAL seconds
"""

import asyncio

from app.db import db_get, db_set
from app.metrics import Metrics

TTL = 300
FLUSH_INTERVAL = 5
DIRTY_SET = "dirty"


async def read(key: str, redis, pool, metrics: Metrics) -> str | None:
    val = await redis.get(key)
    if val is not None:
        metrics.hit()
        return val
    metrics.miss()
    metrics.db_read()
    val = await db_get(pool, key)
    if val is not None:
        await redis.set(key, val, ex=TTL)
    return val


async def write(key: str, value: str, redis, pool, metrics: Metrics) -> None:
    await redis.set(key, value, ex=TTL)
    await redis.sadd(DIRTY_SET, key)


async def flush_once(redis, pool, metrics: Metrics) -> int:
    keys = await redis.smembers(DIRTY_SET)
    if not keys:
        return 0
    flushed = 0
    for key in keys:
        val = await redis.get(key)
        if val is not None:
            await db_set(pool, key, val)
            metrics.db_write()
            flushed += 1
        await redis.srem(DIRTY_SET, key)
    return flushed


async def flush_loop(redis, pool, metrics: Metrics) -> None:
    while True:
        await asyncio.sleep(FLUSH_INTERVAL)
        await flush_once(redis, pool, metrics)
