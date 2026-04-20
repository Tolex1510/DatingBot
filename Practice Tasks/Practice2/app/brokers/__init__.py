from .base import BrokerConsumer, BrokerProducer
from .rabbitmq import RabbitMQConsumer, RabbitMQProducer
from .redis_stream import RedisStreamConsumer, RedisStreamProducer


def make_producer(broker: str, **kwargs) -> BrokerProducer:
    if broker == "rabbitmq":
        return RabbitMQProducer(**kwargs)
    if broker == "redis_stream":
        return RedisStreamProducer(**kwargs)
    raise ValueError(f"unknown broker: {broker}")


def make_consumer(broker: str, **kwargs) -> BrokerConsumer:
    if broker == "rabbitmq":
        return RabbitMQConsumer(**kwargs)
    if broker == "redis_stream":
        return RedisStreamConsumer(**kwargs)
    raise ValueError(f"unknown broker: {broker}")
