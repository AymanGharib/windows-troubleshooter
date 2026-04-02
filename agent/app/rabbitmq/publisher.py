"""
Small RabbitMQ publisher helper for agent status/result messages.
"""

from __future__ import annotations

import json

import pika

from app.config import AppConfig


def publish_message(queue_name: str, event: dict) -> None:
    """Publish a JSON message to a durable RabbitMQ queue."""
    rabbitmq_config = AppConfig.get_rabbitmq_config()
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_config.RABBITMQ_URL))
    try:
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(event, ensure_ascii=False),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )
    finally:
        connection.close()


__all__ = ["publish_message"]
