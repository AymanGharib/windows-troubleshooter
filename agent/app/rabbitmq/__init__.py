"""
RabbitMQ integration package for the incident agent.

This package provides the consumer and publisher helpers used by the
RabbitMQ-driven execution path.
"""

# Import consumer functions
from app.rabbitmq.consumer import (
    report_to_ui,
    process_ticket,
    start_consumer
)
from app.rabbitmq.publisher import publish_message

__all__ = [
    "report_to_ui",
    "process_ticket",
    "start_consumer",
    "publish_message",
]
