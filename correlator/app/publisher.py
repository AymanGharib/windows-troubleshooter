from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Protocol

import pika

from .models import EnrichedIncident
from .rabbitmq_init import ensure_rabbitmq_topology


class Publisher(Protocol):
    async def publish(self, event: EnrichedIncident) -> None:
        ...


class StdoutPublisher:
    async def publish(self, event: EnrichedIncident) -> None:
        print(json.dumps(event.model_dump(mode="json"), ensure_ascii=True))


class JsonlFilePublisher:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def publish(self, event: EnrichedIncident) -> None:
        payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=True)
        await asyncio.to_thread(self._append_line, payload)

    def _append_line(self, payload: str) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(payload + "\n")


class RabbitMQPublisher:
    def __init__(
        self,
        rabbitmq_url: str,
        exchange: str,
        exchange_type: str,
        queue: str,
        routing_key: str,
    ) -> None:
        self.rabbitmq_url = rabbitmq_url
        self.exchange = exchange
        self.exchange_type = exchange_type
        self.queue = queue
        self.routing_key = routing_key

    async def publish(self, event: EnrichedIncident) -> None:
        payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=True)
        await asyncio.to_thread(self._publish_sync, payload)

    def _publish_sync(self, payload: str) -> None:
        connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
        try:
            channel = connection.channel()
            ensure_rabbitmq_topology(
                channel=channel,
                exchange=self.exchange,
                exchange_type=self.exchange_type,
                queue=self.queue,
                routing_key=self.routing_key,
            )
            channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.routing_key,
                body=payload.encode("utf-8"),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
            )
        finally:
            if connection.is_open:
                connection.close()


class NoopPublisher:
    async def publish(self, event: EnrichedIncident) -> None:
        _ = event
