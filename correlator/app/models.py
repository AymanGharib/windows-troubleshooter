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
    sample_count: int = 0
    first_ts_ns: int | None = None
    last_ts_ns: int | None = None
    min_value: float | None = None
    max_value: float | None = None
    current_value: float | None = None
    trend: str = "unknown"


class LogEntry(BaseModel):
    ts_ns: int
    labels: dict[str, str] = Field(default_factory=dict)
    source: str | None = None
    channel: str | None = None
    event_id: int | None = None
    level: str | None = None
    message: str


class Assessment(BaseModel):
    category: str
    probable_cause: str
    confidence: float
    impact: str


class AlertSummary(BaseModel):
    name: str
    status: str
    severity: str | None = None
    summary: str | None = None
    fingerprint: str | None = None


class ScopeSummary(BaseModel):
    host: str
    env: str
    job: str
    resource_type: str
    resource_name: str | None = None


class TimeSummary(BaseModel):
    alert_starts_at: str
    alert_ends_at: str | None = None
    investigation_start: str
    investigation_end: str
    lookback_seconds: int


class MetricSummary(BaseModel):
    name: str
    labels: dict[str, str] = Field(default_factory=dict)
    sample_count: int = 0
    min_value: float | None = None
    max_value: float | None = None
    current_value: float | None = None
    trend: str = "unknown"


class LogSummary(BaseModel):
    matching_log_count: int = 0
    top_signatures: list[dict[str, Any]] = Field(default_factory=list)


class EvidenceSummary(BaseModel):
    metric_summaries: list[MetricSummary] = Field(default_factory=list)
    log_summary: LogSummary


class SignalSummary(BaseModel):
    category: str
    probable_cause: str
    impact: str
    confidence: float


class AgentHints(BaseModel):
    recommended_tools: list[str] = Field(default_factory=list)
    default_log_query: dict[str, Any] = Field(default_factory=dict)
    priority: str = "normal"


class EnrichedIncident(BaseModel):
    event_id: str
    schema_version: str = "2.0"
    generated_at: datetime
    incident_key: str
    alert: AlertSummary
    scope: ScopeSummary
    time: TimeSummary
    signal: SignalSummary
    evidence_summary: EvidenceSummary
    agent_hints: AgentHints
    actions: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    debug: dict[str, Any] | None = None
