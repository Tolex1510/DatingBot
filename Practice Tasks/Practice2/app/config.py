import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    broker: str
    msg_size: int
    rate: int
    duration: int
    amqp_url: str
    redis_url: str
    queue_name: str
    results_dir: str
    run_id: str


def load() -> Settings:
    return Settings(
        broker=os.environ.get("BROKER", "rabbitmq"),
        msg_size=int(os.environ.get("MSG_SIZE", "128")),
        rate=int(os.environ.get("RATE", "1000")),
        duration=int(os.environ.get("DURATION", "30")),
        amqp_url=os.environ.get("AMQP_URL", "amqp://guest:guest@rabbitmq:5672//"),
        redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        queue_name=os.environ.get("QUEUE_NAME", "bench"),
        results_dir=os.environ.get("RESULTS_DIR", "/results"),
        run_id=os.environ.get("RUN_ID", "adhoc"),
    )
