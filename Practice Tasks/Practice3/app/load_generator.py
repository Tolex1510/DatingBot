import asyncio
import random
import time
import types

from app.metrics import Metrics


async def run(
    strategy: types.ModuleType,
    redis,
    pool,
    metrics: Metrics,
    duration: int,
    read_ratio: float,
    n_keys: int,
    concurrency: int,
) -> None:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + duration

    async def worker() -> None:
        while loop.time() < deadline:
            key = f"key:{random.randint(0, n_keys - 1)}"
            t0 = time.perf_counter()
            try:
                if random.random() < read_ratio:
                    await strategy.read(key, redis, pool, metrics)
                else:
                    value = f"v{random.randint(0, 999_999)}"
                    await strategy.write(key, value, redis, pool, metrics)
            except Exception:
                pass
            metrics.record((time.perf_counter() - t0) * 1000)

    await asyncio.gather(*[asyncio.create_task(worker()) for _ in range(concurrency)])
