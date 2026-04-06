"""
Generic RabbitMQ consumer for agent execution.

Consumes task messages, invokes ClaudeAIAgent, and publishes a compact result
message to the configured result queue.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import aio_pika
from aio_pika import IncomingMessage

from app.agent.claude_agent import ClaudeAIAgent
from app.common.utils import get_logger
from app.config import AppConfig
from app.rabbitmq.publisher import publish_message

logger = get_logger(__name__)


def _extract_agent_response_text(result: dict[str, Any]) -> str:
    text = result.get("text")
    if isinstance(text, str):
        return text

    content = result.get("content", [])
    if content and isinstance(content, list):
        first = content[0]
        if isinstance(first, dict):
            return first.get("text", "")
    return ""


def _build_prompt(data: dict[str, Any]) -> str:
    for key in ("prompt", "description", "message", "query", "text"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return json.dumps(data, ensure_ascii=False, indent=2)


def _extract_ids(data: dict[str, Any]) -> tuple[str, str, str]:
    job_id = str(data.get("job_id") or data.get("event_id") or data.get("id") or "")
    ticket_id = str(data.get("ticket_id") or data.get("incident_key") or "")
    reporter_id = str(data.get("reporter_id") or "")
    return job_id, ticket_id, reporter_id


def _publish_result(
    *,
    job_id: str,
    ticket_id: str,
    reporter_id: str,
    status: str,
    message: str,
    result_text: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    rabbitmq_config = AppConfig.get_rabbitmq_config()
    payload: dict[str, Any] = {
        "job_id": job_id,
        "ticket_id": ticket_id,
        "reporter_id": reporter_id,
        "status": status,
        "message": message,
        "result_text": result_text,
    }
    if metadata:
        payload["metadata"] = metadata

    publish_message(rabbitmq_config.RABBITMQ_RESULT_QUEUE, payload)


def _log_result_json(job_id: str, ticket_id: str, result_text: str) -> None:
    """Log agent output, pretty-printing when response is valid JSON."""
    if not result_text:
        logger.info("Agent result is empty job_id=%s ticket_id=%s", job_id, ticket_id)
        return

    candidate = result_text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.startswith("json"):
            candidate = candidate[4:].strip()

    try:
        parsed = json.loads(candidate)
        logger.info(
            "Agent result JSON job_id=%s ticket_id=%s:\n%s",
            job_id,
            ticket_id,
            json.dumps(parsed, ensure_ascii=False, indent=2),
        )
    except Exception:
        logger.info(
            "Agent result (non-JSON) job_id=%s ticket_id=%s:\n%s",
            job_id,
            ticket_id,
            result_text,
        )


async def process_message(message: IncomingMessage) -> None:
    """Process a single queue message and publish agent output."""
    async with message.process():
        body_text = ""
        try:
            body_text = message.body.decode("utf-8", errors="replace")
            data = json.loads(body_text)
        except Exception as exc:
            logger.error("Invalid message body: %s", exc)
            return

        job_id, ticket_id, reporter_id = _extract_ids(data)
        prompt = _build_prompt(data)

        logger.info("Processing RabbitMQ task job_id=%s ticket_id=%s", job_id, ticket_id)

        try:
            agent = ClaudeAIAgent()
            result = await agent.invoke(prompt, context_id="rabbitmq-consumer")
            result_text = _extract_agent_response_text(result)
            metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
            _log_result_json(job_id, ticket_id, result_text)

            _publish_result(
                job_id=job_id,
                ticket_id=ticket_id,
                reporter_id=reporter_id,
                status="COMPLETED",
                message="Task processed successfully",
                result_text=result_text,
                metadata=metadata if isinstance(metadata, dict) else None,
            )
            logger.info("Task completed job_id=%s ticket_id=%s", job_id, ticket_id)
        except Exception as exc:
            logger.error("Error processing with AI Agent: %s", exc, exc_info=True)
            _publish_result(
                job_id=job_id,
                ticket_id=ticket_id,
                reporter_id=reporter_id,
                status="FAILED",
                message=f"Error processing with AI Agent: {exc}",
            )


async def _start_consumer_async() -> None:
    rabbitmq_config = AppConfig.get_rabbitmq_config()
    connection = await aio_pika.connect_robust(rabbitmq_config.RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)

        await channel.declare_exchange(
            rabbitmq_config.RABBITMQ_EXCHANGE,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        queue = await channel.declare_queue(rabbitmq_config.RABBITMQ_TASK_QUEUE, durable=True)
        await queue.bind(
            rabbitmq_config.RABBITMQ_EXCHANGE,
            routing_key=rabbitmq_config.RABBITMQ_ROUTING_KEY,
        )
        await queue.consume(process_message)

        logger.info(
            "Consumer ONLINE queue='%s' exchange='%s' routing_key='%s'",
            rabbitmq_config.RABBITMQ_TASK_QUEUE,
            rabbitmq_config.RABBITMQ_EXCHANGE,
            rabbitmq_config.RABBITMQ_ROUTING_KEY,
        )
        logger.info("Press Ctrl+C to stop...")

        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            pass


def start_consumer() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        asyncio.run(_start_consumer_async())
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as exc:
        logger.error("Consumer error: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    start_consumer()


__all__ = ["process_message", "start_consumer"]
