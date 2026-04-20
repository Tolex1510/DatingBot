# Practice 2. Сравнение RabbitMQ и Redis как брокеров сообщений

Стенд «producer → broker → consumer» на Python (asyncio). Гоняет одинаковую
нагрузку через RabbitMQ и Redis (Streams) и сравнивает пропускную способность,
задержку и точку деградации single-instance.

## Что внутри

- `app/brokers/rabbitmq.py` — продюсер/консюмер на `aio-pika` (durable queue, publisher confirms).
- `app/brokers/redis_stream.py` — продюсер/консюмер на Redis Streams (XADD / XREADGROUP / XACK, consumer group).
- `app/producer.py` — отправитель с token-bucket троттлингом (батчи по 100).
- `app/consumer.py` — потребитель, измеряет latency по timestamp внутри сообщения, считает потери по seq.
- `app/runner.py` — оркестратор: матрица `brokers × msg_size × rate`, запускает producer/consumer как `multiprocessing.Process`, пишет `results/raw.csv`.
- `scripts/plot.py` — графики в `results/plots/`.
- `results/report.md` — итоговый отчёт.

## Матрица экспериментов

| Ось        | Значения                                      |
|------------|-----------------------------------------------|
| brokers    | `rabbitmq`, `redis_stream`                    |
| msg size   | 128 B, 1 KB, 10 KB, 100 KB                    |
| rate       | 1 000, 5 000, 10 000 msg/sec                  |
| duration   | 30 сек на прогон                              |

Итого 24 прогона ≈ 15–20 минут.

Для обоих брокеров одинаковые лимиты в docker-compose: `cpus=2.0`, `memory=1g`.

## Формат сообщения

`JSON` с полями `seq` (последовательный номер, считаем потери),
`ts` (`time.time()` отправителя, считаем latency),
`p` (паддинг до заданного размера).

## Запуск

```bash
cd "Practice Tasks/Practice2"

# 1. прогон всех экспериментов (всё в docker)
docker compose up --build --abort-on-container-exit runner

# 2. графики
docker compose run --rm runner python scripts/plot.py

# 3. скриншоты для отчёта (руками, пока гоняется тяжёлый прогон)
#    - RabbitMQ management UI: http://localhost:15673 (guest/guest)
#    - Redis: docker compose exec redis redis-cli info
#    Сохранить в results/screenshots/

# 4. убрать контейнеры
docker compose down -v
```

Результаты после прогона:
- `results/raw.csv` — по одной строке на прогон (все метрики)
- `results/producer_*.json`, `results/consumer_*.json` — сырые данные
- `results/plots/*.png` — графики
- `results/report.md` — отчёт с таблицей и выводами

## Одиночный прогон (для отладки)

```bash
docker compose up -d rabbitmq redis

# consumer в фоне
BROKER=rabbitmq MSG_SIZE=1024 RATE=5000 DURATION=30 RUN_ID=dbg \
  docker compose run --rm -d runner python -m app.consumer

# producer
BROKER=rabbitmq MSG_SIZE=1024 RATE=5000 DURATION=30 RUN_ID=dbg \
  docker compose run --rm runner python -m app.producer
```

## Замеряемые метрики

- `sent`, `received`, `lost` (по пропускам seq)
- `received_per_sec` — фактический throughput
- `avg_ms`, `p50_ms`, `p95_ms`, `p99_ms`, `max_ms` — end-to-end latency
- `producer_errors` — неудачные publish

## Ограничения стенда

- Один producer / один consumer — по ТЗ (single instance).
- Измерение latency требует синхронного времени producer↔consumer; здесь это один хост,
  поэтому clock skew отсутствует.
- Token-bucket в producer'е не гарантирует точное распределение —
  он лимитирует среднюю скорость батчами по 100.
