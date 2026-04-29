import asyncio
import csv
import os
import time

from redis.asyncio import Redis

from app.config import load
from app.db import create_pool, db_clear, db_set
from app.load_generator import run as generate_load
from app.metrics import Metrics
from app.strategies import cache_aside, write_through, write_back

STRATEGIES = [
    ("cache_aside", cache_aside),
    ("write_through", write_through),
    ("write_back", write_back),
]

SCENARIOS = [
    ("read_heavy",   0.80),
    ("balanced",     0.50),
    ("write_heavy",  0.20),
]

CSV_FIELDS = [
    "strategy", "scenario",
    "throughput", "avg_latency_ms", "db_hits", "cache_hit_rate",
    "total_ops", "dirty_keys_at_end",
]


async def seed(pool, n_keys: int) -> None:
    for i in range(n_keys):
        await db_set(pool, f"key:{i}", f"init_{i}")


async def run_test(strategy_name, strategy_mod, scenario_name, read_ratio, cfg, pool, redis) -> dict:
    await db_clear(pool)
    await redis.flushdb()
    await seed(pool, cfg.n_keys)

    metrics = Metrics()
    flush_task = None

    if strategy_name == "write_back":
        flush_task = asyncio.create_task(
            write_back.flush_loop(redis, pool, metrics)
        )

    t0 = time.perf_counter()
    await generate_load(strategy_mod, redis, pool, metrics, cfg.duration, read_ratio, cfg.n_keys, cfg.concurrency)
    elapsed = time.perf_counter() - t0

    dirty_count = 0
    if strategy_name == "write_back":
        dirty_count = await redis.scard(write_back.DIRTY_SET)
        flush_task.cancel()
        try:
            await flush_task
        except asyncio.CancelledError:
            pass
        flushed = await write_back.flush_once(redis, pool, metrics)
        print(f"  [write_back] dirty keys before final flush: {dirty_count}, flushed now: {flushed}")

    result = metrics.summary(elapsed)
    result["strategy"] = strategy_name
    result["scenario"] = scenario_name
    result["dirty_keys_at_end"] = dirty_count
    return result


async def main() -> None:
    cfg = load()
    os.makedirs(cfg.results_dir, exist_ok=True)

    pool = await create_pool(cfg.database_url)
    redis = Redis.from_url(cfg.redis_url, decode_responses=True)

    print(f"\nConfig: duration={cfg.duration}s  n_keys={cfg.n_keys}  concurrency={cfg.concurrency}")
    print("=" * 60)

    results = []

    for strategy_name, strategy_mod in STRATEGIES:
        for scenario_name, read_ratio in SCENARIOS:
            label = f"{strategy_name} / {scenario_name} ({int(read_ratio*100)}% reads)"
            print(f"\n>>> {label}")

            result = await run_test(strategy_name, strategy_mod, scenario_name, read_ratio, cfg, pool, redis)
            results.append(result)

            print(f"  throughput     : {result['throughput']:.1f} req/s")
            print(f"  avg latency    : {result['avg_latency_ms']:.3f} ms")
            print(f"  db hits        : {result['db_hits']}")
            print(f"  cache hit rate : {result['cache_hit_rate']*100:.1f}%")
            print(f"  total ops      : {result['total_ops']}")

    csv_path = os.path.join(cfg.results_dir, "results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{'='*60}")
    print(f"Results saved → {csv_path}")
    print("Run  python scripts/report.py  to generate report.md")

    await redis.aclose()
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
