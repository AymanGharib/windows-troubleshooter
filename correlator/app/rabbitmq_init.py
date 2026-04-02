from __future__ import annotations

import pika


def ensure_rabbitmq_topology(
    channel: pika.adapters.blocking_connection.BlockingChannel,
    exchange: str,
    exchange_type: str,
    queue: str,
    routing_key: str,
) -> None:
    channel.exchange_declare(exchange=exchange, exchange_type=exchange_type, durable=True)
    channel.queue_declare(queue=queue, durable=True)
    channel.queue_bind(queue=queue, exchange=exchange, routing_key=routing_key)
