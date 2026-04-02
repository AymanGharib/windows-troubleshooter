from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException

from .clients import LokiClient, PrometheusClient
from .config import settings
from .engine import CorrelationEngine
from .models import AlertManagerAlert, AlertManagerWebhook
from .publisher import JsonlFilePublisher, NoopPublisher, RabbitMQPublisher, StdoutPublisher

app = FastAPI(title=settings.app_name)

prom_client = PrometheusClient(settings.prometheus_base_url)
loki_client = LokiClient(settings.loki_base_url)
engine = CorrelationEngine(settings, prom_client, loki_client)
if settings.output_mode == "stdout":
    publisher = StdoutPublisher()
elif settings.output_mode == "file":
    publisher = JsonlFilePublisher(settings.output_file_path)
elif settings.output_mode == "rabbitmq":
    publisher = RabbitMQPublisher(
        rabbitmq_url=settings.rabbitmq_url,
        exchange=settings.rabbitmq_exchange,
        exchange_type=settings.rabbitmq_exchange_type,
        queue=settings.rabbitmq_queue,
        routing_key=settings.rabbitmq_routing_key,
    )
else:
    publisher = NoopPublisher()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "time_utc": datetime.now(UTC).isoformat()}


@app.post("/alert")
async def alert_webhook(payload: AlertManagerWebhook) -> dict:
    if not payload.alerts:
        raise HTTPException(status_code=400, detail="No alerts in payload")

    incidents = []
    for alert in payload.alerts:
        merged_labels = dict(payload.commonLabels)
        merged_labels.update(alert.labels)
        merged_annotations = dict(payload.commonAnnotations)
        merged_annotations.update(alert.annotations)

        merged_alert = alert.model_copy(
            update={
                "labels": merged_labels,
                "annotations": merged_annotations,
            }
        )
        incident = await engine.fetch_and_correlate(merged_alert)
        await publisher.publish(incident)
        incidents.append(incident.model_dump(mode="json"))

    return {"accepted": len(incidents), "incidents": incidents}


@app.post("/test/correlate")
async def test_correlate(alert: AlertManagerAlert) -> dict:
    incident = await engine.fetch_and_correlate(alert)
    await publisher.publish(incident)
    return {"accepted": 1, "incident": incident.model_dump(mode="json")}
