from typing import AsyncIterator

import redis.asyncio as redis
from redis.exceptions import ResponseError

from .base import BrokerConsumer, BrokerProducer

GROUP = "bench_group"
CONSUMER = "consumer1"


class RedisStreamProducer(BrokerProducer):
    def __init__(self, url: str, stream: str, maxlen: int = 1_000_000) -> None:
        self.url = url
        self.stream_key = stream  # атрибут назван не 'stream', чтобы не затенять метод Consumer.stream()
        self.maxlen = maxlen
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        self._client = redis.from_url(self.url)
        try:
            await self._client.xgroup_create(self.stream_key, GROUP, id="0", mkstream=True)
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def send(self, body: bytes) -> None:
        assert self._client is not None
        await self._client.xadd(
            self.stream_key,
            {"d": body},
            maxlen=self.maxlen,
            approximate=True,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()


class RedisStreamConsumer(BrokerConsumer):
    def __init__(self, url: str, stream: str, batch: int = 500) -> None:
        self.url = url
        self.stream_key = stream
        self.batch = batch
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        self._client = redis.from_url(self.url)
        try:
            await self._client.xgroup_create(self.stream_key, GROUP, id="0", mkstream=True)
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def stream(self) -> AsyncIterator[bytes]:
        assert self._client is not None
        while True:
            resp = await self._client.xreadgroup(
                GROUP,
                CONSUMER,
                streams={self.stream_key: ">"},
                count=self.batch,
                block=1000,
            )
            if not resp:
                yield b""  # heartbeat — позволяет внешнему циклу проверить таймаут
                continue
            # resp = [(stream_name, [(msg_id, {b"d": body}), ...])]
            for _stream_name, entries in resp:
                ids = [msg_id for msg_id, _ in entries]
                for _msg_id, fields in entries:
                    yield fields[b"d"]
                await self._client.xack(self.stream_key, GROUP, *ids)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()


async def purge(url: str, stream: str) -> None:
    client = redis.from_url(url)
    try:
        await client.delete(stream)
    finally:
        await client.aclose()
