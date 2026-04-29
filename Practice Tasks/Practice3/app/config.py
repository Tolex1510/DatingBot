import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    database_url: str
    redis_url: str
    results_dir: str
    duration: int
    n_keys: int
    concurrency: int


def load() -> Config:
    return Config(
        database_url=os.environ.get("DATABASE_URL", "postgresql://bench:bench@localhost:5432/cache_bench"),
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        results_dir=os.environ.get("RESULTS_DIR", "./results"),
        duration=int(os.environ.get("DURATION", "30")),
        n_keys=int(os.environ.get("N_KEYS", "1000")),
        concurrency=int(os.environ.get("CONCURRENCY", "20")),
    )
