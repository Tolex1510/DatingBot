import asyncio
from typing import AsyncIterator

import aio_pika
from aio_pika import DeliveryMode, Message

from .base import BrokerConsumer, BrokerProducer


class RabbitMQProducer(BrokerProducer):
    def __init__(self, url: str, queue: str) -> None:
        self.url = url
        self.queue = queue
        self._conn: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._exchange = None

    async def connect(self) -> None:
        self._conn = await aio_pika.connect_robust(self.url)
        # publisher_confirms отключены для честного сравнения с Redis Streams
        # (XADD возвращается после записи в in-memory лог без ack от реплики)
        self._channel = await self._conn.channel(publisher_confirms=False)
        await self._channel.declare_queue(self.queue, durable=True)
        self._exchange = self._channel.default_exchange

    async def send(self, body: bytes) -> None:
        assert self._exchange is not None
        # delivery_mode=TRANSIENT — сообщения живут в памяти, не пишутся на диск.
        # Это симметрично Redis: `--appendonly no --save ""`.
        msg = Message(body, delivery_mode=DeliveryMode.NOT_PERSISTENT)
        await self._exchange.publish(msg, routing_key=self.queue)

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()


class RabbitMQConsumer(BrokerConsumer):
    def __init__(self, url: str, queue: str, prefetch: int = 500) -> None:
        self.url = url
        self.queue = queue
        self.prefetch = prefetch
        self._conn: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._q: aio_pika.abc.AbstractRobustQueue | None = None
        self._local: asyncio.Queue[bytes] | None = None
        self._consumer_tag: str | None = None

    async def connect(self) -> None:
        self._conn = await aio_pika.connect_robust(self.url)
        self._channel = await self._conn.channel()
        await self._channel.set_qos(prefetch_count=self.prefetch)
        self._q = await self._channel.declare_queue(self.queue, durable=True)
        self._local = asyncio.Queue()

        async def _callback(message: aio_pika.abc.AbstractIncomingMessage) -> None:
            async with message.process():
                assert self._local is not None
                await self._local.put(message.body)

        self._consumer_tag = await self._q.consume(_callback)

    async def stream(self) -> AsyncIterator[bytes]:
        assert self._local is not None
        while True:
            try:
                body = await asyncio.wait_for(self._local.get(), timeout=1.0)
            except asyncio.TimeoutError:
                yield b""
                continue
            yield body

    async def close(self) -> None:
        if self._q is not None and self._consumer_tag is not None:
            try:
                await self._q.cancel(self._consumer_tag)
            except Exception:
                pass
        if self._conn is not None:
            await self._conn.close()


async def purge(url: str, queue: str) -> None:
    conn = await aio_pika.connect_robust(url)
    try:
        ch = await conn.channel()
        q = await ch.declare_queue(queue, durable=True)
        await q.purge()
    finally:
        await conn.close()
