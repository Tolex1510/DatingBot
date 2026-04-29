# Practice 3. Cache Strategy Comparison

Three caching strategies — **Cache-Aside**, **Write-Through**, **Write-Back** — tested under identical load against the same PostgreSQL + Redis stack.

## Components

| Component | Technology |
|-----------|-----------|
| Cache     | Redis 7   |
| Database  | PostgreSQL 16 |
| App + Load Generator | Python 3.12 asyncio |

## Strategies

| Strategy | Read | Write |
|----------|------|-------|
| Cache-Aside (Lazy Loading) | cache → miss → DB → populate cache | DB only, invalidate cache |
| Write-Through | cache → miss → DB → populate cache | DB + cache simultaneously |
| Write-Back | cache → miss → DB → populate cache | cache only, flush to DB every 5 s |

## Test Matrix

| Scenario    | Reads | Writes |
|-------------|-------|--------|
| Read-Heavy  | 80 %  | 20 %   |
| Balanced    | 50 %  | 50 %   |
| Write-Heavy | 20 %  | 80 %   |

Each run: **30 seconds**, **1 000 keys**, **20 concurrent workers**.

## Metrics

- `throughput` — req/s
- `avg_latency_ms` — mean operation time
- `db_hits` — total DB reads + writes
- `cache_hit_rate` — cache hits / (hits + misses)
- `dirty_keys_at_end` *(Write-Back only)* — pending writes before final flush

## How to Run

```bash
cd "Practice Tasks/Practice3"

# Run all 9 tests (3 strategies × 3 scenarios)
docker compose up --build --abort-on-container-exit runner

# Generate report.md from results
docker compose run --rm runner python scripts/report.py

# Tear down
docker compose down -v
```

Results are written to `results/results.csv`.  
Report is written to `results/report.md`.
