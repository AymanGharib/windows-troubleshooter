"""
RabbitMQ consumer for incident-driven agent execution.

This module consumes correlated incidents from RabbitMQ, forwards them to the
Claude Agent SDK wrapper, and publishes status updates to the result queue.
"""

from __future__ import annotations

import asyncio
import json
import os
import pika
import re
import sys
from typing import Any

# Add parent directory to path for shared modules.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))

from app.agent.claude_agent import ClaudeAIAgent
from app.agent.incident_prompt_builder import build_incident_prompt
from app.agent.incident_skills import select_incident_skills
from app.agent.result_schema import TroubleshootingResult
from app.common.utils import get_logger
from app.config import AppConfig
from app.rabbitmq.publisher import publish_message
from pydantic import ValidationError

logger = get_logger(__name__)


def report_to_ui(
    job_id: str,
    ticket_id: str,
    reporter_id: str,
    status_type: str,
    level: str,
    source: str,
    message: str,
    status: str | None = None,
    progress: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Publish a progress or status update to the result queue."""
    event = {
        "job_id": job_id,
        "ticket_id": ticket_id,
        "reporter_id": reporter_id,
        "type": status_type,
        "level": level,
        "source": source,
        "message": message,
    }
    if status:
        event["status"] = status
    if progress is not None:
        event["progress"] = progress
    if details:
        event.update(details)

    rabbitmq_config = AppConfig.get_rabbitmq_config()
    publish_message(rabbitmq_config.RABBITMQ_RESULT_QUEUE, event)


def _extract_agent_response_text(result: dict) -> str:
    """Handle the current ClaudeAIAgent return shape with a small fallback."""
    text = result.get("text")
    if isinstance(text, str):
        return text

    content = result.get("content", [])
    if content and isinstance(content, list):
        first = content[0]
        if isinstance(first, dict):
            return first.get("text", "")
    return ""


def _extract_json_payload(response: str) -> dict[str, Any]:
    """Extract JSON payload from plain text or fenced JSON response."""
    json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL)
    json_str = json_match.group(1) if json_match else response
    return json.loads(json_str)


def _build_result_details(result: TroubleshootingResult) -> dict[str, Any]:
    """Convert validated result into compact event metadata."""
    remediation = result.recommended_remediation
    return {
        "mode": result.mode,
        "summary": result.summary,
        "confidence": result.confidence,
        "probable_cause": result.diagnosis.probable_cause,
        "needs_human": result.needs_human,
        "recommended_action": remediation.action,
        "recommended_command": remediation.command,
    }


def process_ticket(
    ch: pika.channel.Channel,
    method: pika.spec.Basic.Deliver,
    properties: pika.spec.BasicProperties,
    body: bytes,
) -> None:
    """Process a correlated incident from RabbitMQ using the Claude agent."""
    job_id = None
    ticket_id = None
    reporter_id = None

    try:
        data = json.loads(body)
        job_id = data.get("event_id") or data.get("incident_key", "")
        ticket_id = data.get("incident_key", "")
        reporter_id = ""
        description = build_incident_prompt(data)

        alert = data.get("alert", {})
        scope = data.get("scope", {})
        alert_name = alert.get("name") or alert.get("labels", {}).get("alertname", "")
        summary = alert.get("summary") or alert.get("annotations", {}).get("summary", "")
        selected_skills = select_incident_skills(data)

        logger.info("=" * 60)
        logger.info("Received incident from queue")
        logger.info("=" * 60)
        logger.info("Event ID: %s", job_id)
        logger.info("Incident Key: %s", ticket_id)
        logger.info("Alert Name: %s", alert_name)
        logger.info("Summary: %s", summary)
        logger.info("Selected Skills: %s", ", ".join(skill.skill_id for skill in selected_skills))
        logger.info(
            "Scope: host=%s resource_type=%s resource_name=%s",
            scope.get("host"),
            scope.get("resource_type"),
            scope.get("resource_name"),
        )
        logger.info("=" * 60)

        report_to_ui(
            job_id,
            ticket_id,
            reporter_id,
            "STATUS_UPDATE",
            "INFO",
            "INCIDENT_AGENT",
            "Incident received. Starting investigation...",
            status="RUNNING",
            progress=10,
        )

        try:
            agent = ClaudeAIAgent()
            logger.info("Sending incident to Claude AI Agent...")

            report_to_ui(
                job_id,
                ticket_id,
                reporter_id,
                "LOG",
                "INFO",
                "CLAUDE_AGENT",
                "Invoking Claude AI Agent for incident investigation...",
                progress=20,
            )

            result = asyncio.run(agent.invoke(description, context_id="rabbitmq-consumer"))
            response = _extract_agent_response_text(result)

            logger.info("=" * 60)
            logger.info("AI agent response")
            logger.info("=" * 60)
            logger.info("Raw Response: %s...", response[:500])
            logger.info("=" * 60)

            try:
                response_data = _extract_json_payload(response)
                parsed_result = TroubleshootingResult.model_validate(response_data)
                details = _build_result_details(parsed_result)

                logger.info("Parsed Status: %s", parsed_result.status)
                logger.info("Parsed Summary: %s", parsed_result.summary)
                logger.info("Parsed Confidence: %.2f", parsed_result.confidence)
                logger.info("Probable Cause: %s", parsed_result.diagnosis.probable_cause)

                report_to_ui(
                    job_id,
                    ticket_id,
                    reporter_id,
                    "LOG",
                    "INFO",
                    "INCIDENT_AGENT",
                    (
                        f"Root cause: {parsed_result.diagnosis.probable_cause} | "
                        f"Confidence: {parsed_result.confidence:.2f}"
                    ),
                    progress=80,
                    details=details,
                )

                if parsed_result.status == "NEEDS_INFO":
                    logger.warning("Incident investigation requires additional context")
                    report_to_ui(
                        job_id,
                        ticket_id,
                        reporter_id,
                        "STATUS_UPDATE",
                        "WARNING",
                        "INCIDENT_AGENT",
                        parsed_result.summary,
                        status="NEEDS_INFO",
                        progress=100,
                        details=details,
                    )
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info("Incident marked as NEEDS_INFO for incident key %s", ticket_id)
                    logger.info("=" * 60)
                    return

                report_to_ui(
                    job_id,
                    ticket_id,
                    reporter_id,
                    "STATUS_UPDATE",
                    "INFO",
                    "INCIDENT_AGENT",
                    parsed_result.summary,
                    status=parsed_result.status,
                    progress=100,
                    details=details,
                )

            except json.JSONDecodeError as e:
                logger.error("AI response is not valid JSON: %s", e)

                if not response or response.strip() == "":
                    error_message = "There is a problem in the AI platform. Please check Langfuse for details."
                    logger.error("AI response is empty")
                    report_to_ui(
                        job_id,
                        ticket_id,
                        reporter_id,
                        "LOG",
                        "ERROR",
                        "CLAUDE_AGENT",
                        error_message,
                        progress=50,
                    )
                    report_to_ui(
                        job_id,
                        ticket_id,
                        reporter_id,
                        "STATUS_UPDATE",
                        "ERROR",
                        "INCIDENT_AGENT",
                        error_message,
                        status="FAILED",
                        progress=100,
                    )
                else:
                    report_to_ui(
                        job_id,
                        ticket_id,
                        reporter_id,
                        "LOG",
                        "ERROR",
                        "CLAUDE_AGENT",
                        f"AI response is not valid JSON. Raw response: {response[:200]}...",
                        progress=50,
                    )
                    report_to_ui(
                        job_id,
                        ticket_id,
                        reporter_id,
                        "STATUS_UPDATE",
                        "ERROR",
                        "INCIDENT_AGENT",
                        f"Failed to parse AI response as JSON. Error: {str(e)}",
                        status="FAILED",
                        progress=100,
                    )
            except ValidationError as e:
                logger.error("AI response failed schema validation: %s", e)
                report_to_ui(
                    job_id,
                    ticket_id,
                    reporter_id,
                    "LOG",
                    "ERROR",
                    "INCIDENT_AGENT",
                    f"AI response failed schema validation: {str(e)[:300]}",
                    progress=50,
                )
                report_to_ui(
                    job_id,
                    ticket_id,
                    reporter_id,
                    "STATUS_UPDATE",
                    "ERROR",
                    "INCIDENT_AGENT",
                    "AI response did not match the troubleshooting result schema.",
                    status="FAILED",
                    progress=100,
                )

        except Exception as e:
            error_msg = f"Error processing with AI Agent: {str(e)}"
            logger.error(error_msg, exc_info=True)
            report_to_ui(
                job_id,
                ticket_id,
                reporter_id,
                "STATUS_UPDATE",
                "ERROR",
                "INCIDENT_AGENT",
                error_msg,
                status="FAILED",
                progress=100,
            )

        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Message acknowledged and processing completed for incident key %s", ticket_id)
        logger.info("=" * 60)

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse message body: {e}"
        logger.error(error_msg)
        if job_id:
            report_to_ui(
                job_id,
                ticket_id or "",
                reporter_id or "",
                "STATUS_UPDATE",
                "ERROR",
                "INCIDENT_AGENT",
                error_msg,
                status="FAILED",
            )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        error_msg = f"Error processing incident: {e}"
        logger.error(error_msg, exc_info=True)
        if job_id:
            report_to_ui(
                job_id,
                ticket_id or "",
                reporter_id or "",
                "STATUS_UPDATE",
                "ERROR",
                "INCIDENT_AGENT",
                error_msg,
                status="FAILED",
            )
        ch.basic_ack(delivery_tag=method.delivery_tag)


def start_consumer() -> None:
    """Start the RabbitMQ consumer for correlated incidents."""
    rabbitmq_config = AppConfig.get_rabbitmq_config()

    try:
        connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_config.RABBITMQ_URL))
        channel = connection.channel()

        channel.exchange_declare(
            exchange=rabbitmq_config.RABBITMQ_EXCHANGE,
            exchange_type=rabbitmq_config.RABBITMQ_EXCHANGE_TYPE,
            durable=True,
        )
        channel.queue_declare(queue=rabbitmq_config.RABBITMQ_TASK_QUEUE, durable=True)
        channel.queue_bind(
            queue=rabbitmq_config.RABBITMQ_TASK_QUEUE,
            exchange=rabbitmq_config.RABBITMQ_EXCHANGE,
            routing_key=rabbitmq_config.RABBITMQ_ROUTING_KEY,
        )

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=rabbitmq_config.RABBITMQ_TASK_QUEUE,
            on_message_callback=process_ticket,
        )

        logger.info(
            "Incident Agent Consumer is ONLINE. Listening on queue '%s' bound to '%s' with routing key '%s'",
            rabbitmq_config.RABBITMQ_TASK_QUEUE,
            rabbitmq_config.RABBITMQ_EXCHANGE,
            rabbitmq_config.RABBITMQ_ROUTING_KEY,
        )
        logger.info("Press Ctrl+C to stop...")

        channel.start_consuming()

    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error("Consumer error: %s", e)
        raise
    finally:
        if "connection" in locals() and connection.is_open:
            connection.close()
            logger.info("RabbitMQ connection closed")


if __name__ == "__main__":
    start_consumer()


__all__ = ["report_to_ui", "process_ticket", "start_consumer"]
