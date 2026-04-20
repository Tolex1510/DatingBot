import asyncio
import csv
import json
import multiprocessing as mp
import os
import sys
import time

from . import consumer as consumer_mod
from . import producer as producer_mod
from .brokers import rabbitmq as rmq_broker
from .brokers import redis_stream as redis_broker
from .config import load

BROKERS = ["rabbitmq", "redis_stream"]
MSG_SIZES = [128, 1024, 10240, 102400]
RATES = [1000, 5000, 10000]
DURATION = 30
COOLDOWN = 3


def _producer_entry(env: dict) -> None:
    for k, v in env.items():
        os.environ[k] = str(v)
    asyncio.run(producer_mod.run())


def _consumer_entry(env: dict) -> None:
    for k, v in env.items():
        os.environ[k] = str(v)
    asyncio.run(consumer_mod.run())


def _spawn(target, env: dict) -> mp.Process:
    p = mp.Process(target=target, args=(env,), daemon=False)
    p.start()
    return p


async def _purge(broker: str, base: dict) -> None:
    if broker == "rabbitmq":
        await rmq_broker.purge(base["AMQP_URL"], base["QUEUE_NAME"])
    else:
        await redis_broker.purge(base["REDIS_URL"], base["QUEUE_NAME"])


def _run_id(broker: str, size: int, rate: int) -> str:
    return f"{broker}_{size}_{rate}"


def _read_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def run_experiment(broker: str, size: int, rate: int, base_env: dict, results_dir: str) -> dict:
    run_id = _run_id(broker, size, rate)
    env = {
        **base_env,
        "BROKER": broker,
        "MSG_SIZE": size,
        "RATE": rate,
        "DURATION": DURATION,
        "RUN_ID": run_id,
    }
    print(f"\n=== {run_id} ===", flush=True)

    asyncio.run(_purge(broker, env))

    cons = _spawn(_consumer_entry, env)
    time.sleep(2)  # даём consumer'у подключиться и создать группу/подписку
    prod = _spawn(_producer_entry, env)

    prod.join(timeout=DURATION + 60)
    if prod.is_alive():
        prod.terminate()
    cons.join(timeout=DURATION + 60)
    if cons.is_alive():
        cons.terminate()

    prod_result = _read_json(os.path.join(results_dir, f"producer_{run_id}.json"))
    cons_result = _read_json(os.path.join(results_dir, f"consumer_{run_id}.json"))

    sent = prod_result.get("sent", 0)
    received = cons_result.get("received", 0)
    lost = cons_result.get("lost", 0)
    row = {
        "broker": broker,
        "msg_size": size,
        "target_rate": rate,
        "duration": DURATION,
        "sent": sent,
        "received": received,
        "lost": lost,
        "received_per_sec": round(received / DURATION, 1) if DURATION else 0,
        "avg_ms": cons_result.get("avg_ms", 0),
        "p50_ms": cons_result.get("p50_ms", 0),
        "p95_ms": cons_result.get("p95_ms", 0),
        "p99_ms": cons_result.get("p99_ms", 0),
        "max_ms": cons_result.get("max_ms", 0),
        "producer_errors": prod_result.get("errors", 0),
    }
    print(f"[row] {row}", flush=True)
    return row


def main() -> None:
    s = load()
    results_dir = s.results_dir
    os.makedirs(results_dir, exist_ok=True)

    base_env = {
        "AMQP_URL": s.amqp_url,
        "REDIS_URL": s.redis_url,
        "QUEUE_NAME": s.queue_name,
        "RESULTS_DIR": results_dir,
    }

    csv_path = os.path.join(results_dir, "raw.csv")
    fieldnames = [
        "broker", "msg_size", "target_rate", "duration",
        "sent", "received", "lost", "received_per_sec",
        "avg_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms",
        "producer_errors",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for broker in BROKERS:
            for size in MSG_SIZES:
                for rate in RATES:
                    row = run_experiment(broker, size, rate, base_env, results_dir)
                    writer.writerow(row)
                    f.flush()
                    time.sleep(COOLDOWN)

    print(f"\nDone. CSV: {csv_path}")


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
