"""
RabbitMQSettings: RabbitMQ-related configuration loaded from environment.

Env vars:
- RABBITMQ_URL (required for RabbitMQ connection)
- RABBITMQ_TASK_QUEUE (optional, default: "agent.incidents.tasks")
- RABBITMQ_RESULT_QUEUE (optional, default: "agent.results")
- RABBITMQ_EXCHANGE (optional, default: "incidents.topic")
- RABBITMQ_EXCHANGE_TYPE (optional, default: "topic")
- RABBITMQ_ROUTING_KEY (optional, default: "incidents.correlator.enriched")
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RabbitMQSettings:
    RABBITMQ_URL: str
    RABBITMQ_TASK_QUEUE: str
    RABBITMQ_RESULT_QUEUE: str
    RABBITMQ_EXCHANGE: str
    RABBITMQ_EXCHANGE_TYPE: str
    RABBITMQ_ROUTING_KEY: str


def load_rabbitmq_settings() -> RabbitMQSettings:
    return RabbitMQSettings(
        RABBITMQ_URL=os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"),
        RABBITMQ_TASK_QUEUE=os.getenv("RABBITMQ_TASK_QUEUE", "agent.incidents.tasks"),
        RABBITMQ_RESULT_QUEUE=os.getenv("RABBITMQ_RESULT_QUEUE", "agent.results"),
        RABBITMQ_EXCHANGE=os.getenv("RABBITMQ_EXCHANGE", "incidents.topic"),
        RABBITMQ_EXCHANGE_TYPE=os.getenv("RABBITMQ_EXCHANGE_TYPE", "topic"),
        RABBITMQ_ROUTING_KEY=os.getenv("RABBITMQ_ROUTING_KEY", "incidents.correlator.enriched"),
    )


# Singleton settings object used across the app
rabbitmq_settings: RabbitMQSettings = load_rabbitmq_settings()
