from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AlertManagerAlert(BaseModel):
    status: str
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: datetime
    endsAt: datetime | None = None
    generatorURL: str | None = None
    fingerprint: str | None = None


class AlertManagerWebhook(BaseModel):
    receiver: str
    status: str
    alerts: list[AlertManagerAlert]
    groupLabels: dict[str, str] = Field(default_factory=dict)
    commonLabels: dict[str, str] = Field(default_factory=dict)
    commonAnnotations: dict[str, str] = Field(default_factory=dict)
    externalURL: str | None = None
    version: str | None = None
    groupKey: str | None = None
    truncatedAlerts: int | None = 0


class TimeWindow(BaseModel):
    start_ns: int
    end_ns: int


class MetricPoint(BaseModel):
    ts_ns: int
    value: float


class MetricSeries(BaseModel):
    name: str
    labels: dict[str, str] = Field(default_factory=dict)
    points: list[MetricPoint] = Field(default_factory=list)
    min_value: float | None = None
    max_value: float | None = None
    current_value: float | None = None
    trend: str = "unknown"


class LogEntry(BaseModel):
    ts_ns: int
    labels: dict[str, str] = Field(default_factory=dict)
    line: str


class Assessment(BaseModel):
    category: str
    probable_cause: str
    confidence: float
    impact: str


class EnrichedIncident(BaseModel):
    event_id: str
    schema_version: str = "1.0"
    generated_at: datetime
    incident_key: str
    alert: dict[str, Any]
    scope: dict[str, Any]
    window: dict[str, Any]
    evidence: dict[str, Any]
    assessment: Assessment
    actions: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    debug: dict[str, Any] | None = None
