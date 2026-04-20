from abc import ABC, abstractmethod
from typing import AsyncIterator


class BrokerProducer(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def send(self, body: bytes) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...


class BrokerConsumer(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    def stream(self) -> AsyncIterator[bytes]: ...

    @abstractmethod
    async def close(self) -> None: ...
