import asyncio
import json
import os
import time

from .brokers import make_producer
from .config import load
from .message import build

BATCH = 100  # сколько сообщений отправлять до следующей проверки расписания


async def run() -> None:
    s = load()
    url = s.amqp_url if s.broker == "rabbitmq" else s.redis_url
    producer = make_producer(s.broker, url=url, **(
        {"queue": s.queue_name} if s.broker == "rabbitmq" else {"stream": s.queue_name}
    ))
    await producer.connect()

    interval = BATCH / s.rate  # сек на один батч
    sent = 0
    errors = 0
    deadline = time.monotonic() + s.duration
    seq = 0

    while time.monotonic() < deadline:
        batch_start = time.monotonic()
        for _ in range(BATCH):
            if time.monotonic() >= deadline:
                break
            try:
                await producer.send(build(seq, s.msg_size))
                sent += 1
            except Exception:
                errors += 1
            seq += 1
        elapsed = time.monotonic() - batch_start
        sleep_for = interval - elapsed
        if sleep_for > 0:
            await asyncio.sleep(sleep_for)

    await producer.close()

    result = {
        "run_id": s.run_id,
        "broker": s.broker,
        "msg_size": s.msg_size,
        "target_rate": s.rate,
        "duration": s.duration,
        "sent": sent,
        "errors": errors,
        "max_seq": seq - 1,
    }
    os.makedirs(s.results_dir, exist_ok=True)
    path = os.path.join(s.results_dir, f"producer_{s.run_id}.json")
    with open(path, "w") as f:
        json.dump(result, f)
    print(f"[producer] {result}")


if __name__ == "__main__":
    asyncio.run(run())
