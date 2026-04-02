from __future__ import annotations

import hashlib
import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from .clients import LokiClient, PrometheusClient
from .config import Settings
from .models import (
    AlertManagerAlert,
    Assessment,
    EnrichedIncident,
    LogEntry,
    MetricPoint,
    MetricSeries,
    TimeWindow,
)
from .time_utils import build_window_from_alert, ns_to_datetime, seconds_to_ns


class CorrelationEngine:
    def __init__(self, settings: Settings, prom: PrometheusClient, loki: LokiClient) -> None:
        self.settings = settings
        self.prom = prom
        self.loki = loki

    def build_incident_key(self, alert: AlertManagerAlert) -> str:
        host = alert.labels.get("host", "unknown-host")
        alert_name = alert.labels.get("alertname", "unknown-alert")
        base = f"{alert.fingerprint or 'nofp'}::{host}::{alert_name}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]

    def build_window(self, alert: AlertManagerAlert) -> TimeWindow:
        is_resolved = alert.status == "resolved"
        ends_at = self._normalize_ends_at(alert.endsAt)
        return build_window_from_alert(
            starts_at=alert.startsAt,
            ends_at=ends_at,
            lookback_seconds=self.settings.default_lookback_seconds,
            is_resolved=is_resolved,
        )

    def build_prom_queries(self, alert: AlertManagerAlert) -> list[tuple[str, str]]:
        host = alert.labels.get("host", "my-desktop")
        alert_name = alert.labels.get("alertname", "")
        base_host = f'{{host="{host}"}}'
        process_selector = self._build_process_selector(alert)
        service_selector = self._build_service_selector(alert)

        query_map: dict[str, list[tuple[str, str]]] = {
            "HighCPU": [
                ("host_cpu_pct", f'100 - (avg(rate(windows_cpu_time_total{{mode="idle"}}[2m])) * 100)'),
            ],
            "HighMemory": [
                (
                    "host_memory_pct",
                    "100 - (windows_os_physical_memory_free_bytes / windows_cs_physical_memory_bytes * 100)",
                ),
            ],
            "LowDisk": [
                (
                    "disk_c_free_pct",
                    '(windows_logical_disk_free_bytes{volume="C:"} / windows_logical_disk_size_bytes{volume="C:"} * 100)',
                ),
            ],
            "ProcessDown": [
                (
                    "process_absent",
                    f"absent_over_time(windows_process_cpu_time_total{{mode=\"user\",{process_selector}}}[1m])",
                ),
            ],
            "ProcessHighCPU": [
                (
                    "process_cpu_pct",
                    f"rate(windows_process_cpu_time_total{{mode=\"user\",{process_selector}}}[2m]) * 100",
                ),
            ],
            "ProcessHighMemory": [
                (
                    "process_memory_bytes",
                    f"windows_process_working_set_bytes{{{process_selector}}}",
                ),
            ],
            "ServiceDown": [
                (
                    "service_running_state",
                    f'windows_service_state{{state="running",{service_selector}}}',
                ),
            ],
        }
        selected = query_map.get(alert_name, [("up_signal", "up")])
        out: list[tuple[str, str]] = []
        for name, q in selected:
            if "{" in q and "host=" not in q:
                out.append((name, self._inject_label_matcher(q, base_host)))
            else:
                out.append((name, q))
        return out

    def _build_process_selector(self, alert: AlertManagerAlert) -> str:
        process_name = alert.labels.get("process") or alert.labels.get("name")
        if process_name:
            return f'process=~"(?i)^{re.escape(process_name)}$"'
        return f'process=~"{self.settings.watched_process_regex}"'

    def _build_service_selector(self, alert: AlertManagerAlert) -> str:
        service_name = alert.labels.get("name")
        if service_name:
            return f'name="{service_name}"'
        return 'name=~"my-service|my-worker|my-api"'

    def build_loki_queries(self, alert: AlertManagerAlert) -> list[str]:
        host = alert.labels.get("host")
        alert_name = alert.labels.get("alertname", "")
        stream_with_host = f'{{job="windows-eventlog",host="{host}"}}' if host else ""
        stream_any_host = '{job="windows-eventlog"}'

        pattern_map = {
            "ServiceDown": "Service Control Manager|7000|7009|7040|7045",
            "ProcessDown": "terminated|crash|failed",
            "ProcessHighCPU": "timeout|slow|blocked",
            "ProcessHighMemory": "out of memory|memory|allocation",
            "HighCPU": "cpu|processor|throttle|timeout",
            "HighMemory": "memory|commit|paging|low virtual",
            "LowDisk": "disk|ntfs|volsnap|space",
        }
        patt = pattern_map.get(alert_name, "error|fail|critical")
        queries: list[str] = []
        if stream_with_host:
            queries.append(f'{stream_with_host} |~ "(?i){patt}"')
            queries.append(stream_with_host)
        queries.append(f'{stream_any_host} |~ "(?i){patt}"')
        queries.append(stream_any_host)
        return queries

    async def fetch_and_correlate(self, alert: AlertManagerAlert) -> EnrichedIncident:
        data_gaps: list[str] = []
        window = self.build_window(alert)
        prom_raw: dict[str, Any] = {}
        loki_raw: dict[str, Any] = {}
        debug_block: dict[str, Any] | None = None
        prom_debug_queries: list[dict[str, str]] = []
        loki_debug_queries: list[dict[str, str]] = []

        prom_queries = self.build_prom_queries(alert)
        loki_queries = self.build_loki_queries(alert)

        try:
            for metric_name, q in prom_queries:
                if self.settings.debug_include_query_output:
                    prom_debug_queries.append({"name": metric_name, "query": q})
                prom_raw[metric_name] = await self.prom.query_range(q, window.start_ns, window.end_ns)
        except Exception as exc:
            data_gaps.append(f"prometheus_unavailable:{type(exc).__name__}")

        try:
            for idx, q in enumerate(loki_queries):
                if self.settings.debug_include_query_output:
                    loki_debug_queries.append({"name": f"q{idx + 1}", "query": q})
                loki_raw[f"q{idx + 1}"] = await self.loki.query_range(
                    q,
                    window.start_ns,
                    window.end_ns,
                    limit=self.settings.max_logs_per_event * 3,
                )
        except Exception as exc:
            data_gaps.append(f"loki_unavailable:{type(exc).__name__}")

        metrics_norm = self.normalize_metrics(prom_raw)
        logs_norm = self.normalize_logs(loki_raw)

        corr = self.correlate_evidence(alert, metrics_norm, logs_norm, window)
        assessment = self.infer_assessment(alert, corr["signal_score"], corr["log_score"], corr["top_log_signatures"])
        actions = self.recommend_actions(assessment.category)
        if not metrics_norm:
            data_gaps.append("no_prometheus_evidence")
        if not logs_norm:
            data_gaps.append("no_loki_evidence")

        if self.settings.debug_include_query_output:
            debug_block = {
                "window_ns": {"start": window.start_ns, "end": window.end_ns},
                "prometheus": {
                    "queries": prom_debug_queries,
                    "raw": self._truncate_payload(prom_raw),
                },
                "loki": {
                    "queries": loki_debug_queries,
                    "raw": self._truncate_payload(loki_raw),
                },
            }

        incident = EnrichedIncident(
            event_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            incident_key=self.build_incident_key(alert),
            alert={
                "status": alert.status,
                "labels": alert.labels,
                "annotations": alert.annotations,
                "starts_at": alert.startsAt.isoformat(),
                "ends_at": self._serialize_ends_at(alert.endsAt),
                "fingerprint": alert.fingerprint,
            },
            scope={
                "host": alert.labels.get("host", "unknown-host"),
                "env": alert.labels.get("env", self.settings.app_env),
                "job": alert.labels.get("job", "unknown-job"),
            },
            window={
                "start_ns": window.start_ns,
                "end_ns": window.end_ns,
                "start_utc": ns_to_datetime(window.start_ns).isoformat(),
                "end_utc": ns_to_datetime(window.end_ns).isoformat(),
                "lookback_seconds": self.settings.default_lookback_seconds,
            },
            evidence={
                "metrics": [series.model_dump() for series in metrics_norm],
                "logs": [entry.model_dump() for entry in logs_norm],
                "signal_score": corr["signal_score"],
                "log_score": corr["log_score"],
                "top_log_signatures": corr["top_log_signatures"],
            },
            assessment=assessment,
            actions=actions,
            data_gaps=data_gaps,
            debug=debug_block,
        )
        return incident

    def normalize_metrics(self, prom_raw: dict[str, Any]) -> list[MetricSeries]:
        series_out: list[MetricSeries] = []
        for metric_name, payload in prom_raw.items():
            results = payload.get("data", {}).get("result", [])
            for item in results:
                labels = item.get("metric", {})
                values = item.get("values", [])
                points = []
                for raw_ts, raw_val in values[: self.settings.max_metric_points_per_series]:
                    try:
                        points.append(MetricPoint(ts_ns=seconds_to_ns(float(raw_ts)), value=float(raw_val)))
                    except ValueError:
                        continue
                if not points:
                    continue
                vals = [p.value for p in points]
                trend = "flat"
                if len(vals) >= 2:
                    delta = vals[-1] - vals[0]
                    if delta > 0.5:
                        trend = "up"
                    elif delta < -0.5:
                        trend = "down"
                series_out.append(
                    MetricSeries(
                        name=metric_name,
                        labels=labels,
                        points=points,
                        min_value=min(vals),
                        max_value=max(vals),
                        current_value=vals[-1],
                        trend=trend,
                    )
                )
        return series_out

    def normalize_logs(self, loki_raw: dict[str, Any]) -> list[LogEntry]:
        dedup = {}
        for payload in loki_raw.values():
            streams = payload.get("data", {}).get("result", [])
            for stream in streams:
                labels = stream.get("stream", {})
                for raw_ts, line in stream.get("values", []):
                    sig = self._line_signature(line)
                    if sig in dedup:
                        continue
                    try:
                        ts_ns = int(raw_ts)
                    except (TypeError, ValueError):
                        continue
                    dedup[sig] = LogEntry(ts_ns=ts_ns, labels=labels, line=line.strip())

        ordered = sorted(dedup.values(), key=lambda x: x.ts_ns, reverse=True)
        return ordered[: self.settings.max_logs_per_event]

    def correlate_evidence(
        self,
        alert: AlertManagerAlert,
        metrics: list[MetricSeries],
        logs: list[LogEntry],
        window: TimeWindow,
    ) -> dict[str, Any]:
        signal_score = 0.0
        for series in metrics:
            if series.current_value is None:
                continue
            alert_name = alert.labels.get("alertname", "")
            val = series.current_value
            if alert_name == "HighCPU" and val > 80:
                signal_score += 0.4
            elif alert_name == "HighMemory" and val > 85:
                signal_score += 0.4
            elif alert_name == "LowDisk" and val < 15:
                signal_score += 0.4
            elif alert_name == "ProcessDown" and val > 0:
                signal_score += 0.6
            elif alert_name == "ServiceDown" and val <= 0:
                signal_score += 0.6
            elif alert_name in {"ProcessHighCPU", "ProcessHighMemory"}:
                signal_score += 0.3
            else:
                signal_score += 0.1
        signal_score = min(signal_score, 1.0)

        top_log_signatures: dict[str, int] = defaultdict(int)
        start, end = window.start_ns, window.end_ns
        for entry in logs:
            if start <= entry.ts_ns <= end:
                top_log_signatures[self._line_signature(entry.line)] += 1

        log_score = min(1.0, 0.1 * len(top_log_signatures))
        top_sorted = sorted(top_log_signatures.items(), key=lambda x: x[1], reverse=True)[:5]
        return {
            "signal_score": round(signal_score, 3),
            "log_score": round(log_score, 3),
            "top_log_signatures": [{"signature": k, "count": v} for k, v in top_sorted],
        }

    def infer_assessment(
        self,
        alert: AlertManagerAlert,
        signal_score: float,
        log_score: float,
        top_log_signatures: list[dict[str, Any]],
    ) -> Assessment:
        alert_name = alert.labels.get("alertname", "UnknownAlert")
        combined = min(1.0, 0.65 * signal_score + 0.35 * log_score)

        mapping = {
            "HighCPU": ("resource_pressure", "host_cpu_saturation", "performance_degradation"),
            "HighMemory": ("resource_pressure", "host_memory_pressure", "performance_degradation"),
            "LowDisk": ("capacity_risk", "system_disk_low_space", "write_failures_risk"),
            "ProcessDown": ("availability", "process_not_running", "service_unavailable"),
            "ProcessHighCPU": ("process_resource_pressure", "process_cpu_hotspot", "slow_responses"),
            "ProcessHighMemory": ("process_resource_pressure", "process_memory_growth", "oom_risk"),
            "ServiceDown": ("availability", "windows_service_stopped", "service_unavailable"),
        }
        category, cause, impact = mapping.get(alert_name, ("unknown", "unknown_cause", "unknown_impact"))

        if top_log_signatures and category == "unknown":
            cause = "log_indicated_runtime_issue"
        return Assessment(category=category, probable_cause=cause, confidence=round(combined, 3), impact=impact)

    def recommend_actions(self, category: str) -> list[str]:
        action_map = {
            "resource_pressure": [
                "Identify top CPU/memory consumers over the alert window.",
                "Throttle or restart the heaviest process if policy allows.",
            ],
            "capacity_risk": [
                "Free disk space on C: by removing transient files and old logs.",
                "Verify backup/snapshot growth settings if volsnap/ntfs events exist.",
            ],
            "availability": [
                "Inspect service/process startup configuration and dependency chain.",
                "Attempt controlled restart and monitor for repeated failure.",
            ],
            "process_resource_pressure": [
                "Capture process diagnostics (CPU/memory profile) near alert time.",
                "Scale limits or tune workload/concurrency for the process.",
            ],
            "unknown": [
                "Collect additional logs around the alert window.",
                "Run targeted health checks before remediation.",
            ],
        }
        return action_map.get(category, action_map["unknown"])

    @staticmethod
    def _inject_label_matcher(query: str, host_matcher: str) -> str:
        # Query already has selectors; merge host label into each top-level selector block.
        # This is intentionally conservative and keeps queries human-readable.
        if "host=" in query:
            return query
        host_part = host_matcher.strip("{}")
        return query.replace("{", "{" + host_part + ",", 1)

    @staticmethod
    def _line_signature(line: str) -> str:
        normalized = " ".join(line.lower().split())
        if len(normalized) > 120:
            normalized = normalized[:120]
        return normalized

    def _truncate_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        max_chars = self.settings.debug_max_chars_per_payload
        text = str(payload)
        if len(text) <= max_chars:
            return payload
        return {
            "truncated": True,
            "preview": text[:max_chars],
            "original_size_chars": len(text),
        }

    @staticmethod
    def _normalize_ends_at(ends_at: datetime | None) -> datetime | None:
        if not ends_at:
            return None
        if ends_at.year <= 1:
            return None
        return ends_at

    def _serialize_ends_at(self, ends_at: datetime | None) -> str | None:
        normalized = self._normalize_ends_at(ends_at)
        return normalized.isoformat() if normalized else None
