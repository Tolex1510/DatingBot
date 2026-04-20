import asyncio
import json
import os
import time

from .brokers import make_consumer
from .config import load
from .message import parse
from .metrics import summarize

IDLE_TIMEOUT = 5.0  # сек пустого стрима подряд → завершаем


async def run() -> None:
    s = load()
    url = s.amqp_url if s.broker == "rabbitmq" else s.redis_url
    consumer = make_consumer(s.broker, url=url, **(
        {"queue": s.queue_name} if s.broker == "rabbitmq" else {"stream": s.queue_name}
    ))
    await consumer.connect()

    latencies_ms: list[float] = []
    seqs: set[int] = set()
    received = 0
    # общий дедлайн — duration + большой буфер на доезжающие сообщения
    hard_deadline = time.monotonic() + s.duration + 30
    last_msg_at = time.monotonic()

    try:
        async for body in consumer.stream():
            now = time.monotonic()
            if now > hard_deadline:
                break
            if not body:
                # heartbeat из redis_stream: проверяем idle-таймаут
                if now - last_msg_at > IDLE_TIMEOUT:
                    break
                continue
            try:
                seq, ts = parse(body)
            except Exception:
                continue
            latencies_ms.append((time.time() - ts) * 1000.0)
            seqs.add(seq)
            received += 1
            last_msg_at = now
            # для RabbitMQ нет heartbeat — проверяем дедлайн периодически
            if received % 1000 == 0 and now > hard_deadline:
                break
    except asyncio.CancelledError:
        pass

    await consumer.close()

    max_seq = max(seqs) if seqs else -1
    expected = max_seq + 1
    lost = max(expected - received, 0)

    summary = summarize(latencies_ms)
    result = {
        "run_id": s.run_id,
        "broker": s.broker,
        "msg_size": s.msg_size,
        "target_rate": s.rate,
        "duration": s.duration,
        "received": received,
        "lost": lost,
        **summary,
    }
    os.makedirs(s.results_dir, exist_ok=True)
    path = os.path.join(s.results_dir, f"consumer_{s.run_id}.json")
    with open(path, "w") as f:
        json.dump(result, f)
    print(f"[consumer] {result}")


if __name__ == "__main__":
    asyncio.run(run())
