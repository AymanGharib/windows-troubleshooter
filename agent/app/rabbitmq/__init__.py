"""RabbitMQ integration package for queue-based agent execution."""

from app.rabbitmq.consumer import process_message, start_consumer
from app.rabbitmq.publisher import publish_message

__all__ = [
    "process_message",
    "start_consumer",
    "publish_message",
]
