"""
Write-Through

READ:  cache → miss → DB → populate cache
WRITE: DB and cache simultaneously
"""

from app.db import db_get, db_set
from app.metrics import Metrics

TTL = 300


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
    metrics.db_write()
    await db_set(pool, key, value)
    await redis.set(key, value, ex=TTL)
