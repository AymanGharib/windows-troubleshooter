"""
Incident skill registry for deterministic, incident-native prompt routing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IncidentSkill:
    """Structured definition for an incident skill pack."""

    skill_id: str
    title: str
    description: str
    applies_when: tuple[str, ...]
    investigation_steps: tuple[str, ...]
    tool_usage: tuple[str, ...]
    allowed_tools: tuple[str, ...] = field(default_factory=tuple)


PROCESS_AVAILABILITY_SKILL = IncidentSkill(
    skill_id="process_availability",
    title="Process Availability",
    description=(
        "Use this skill when the incident says a watched process is missing, absent, "
        "or unhealthy and the main task is to determine whether the process crashed, "
        "never started, or is indirectly down because a service failed."
    ),
    applies_when=(
        "Use when alert.name is ProcessDown.",
        "Use when scope.resource_type is process.",
        "Use when signal.probable_cause suggests process_not_running or process absence.",
    ),
    investigation_steps=(
        "Confirm whether the process is currently absent or only absent during the incident window.",
        "Check whether the process should be service-backed or manually launched.",
        "Look for crash, startup, dependency, or access-denied evidence before suggesting action.",
        "If logs are empty, say so clearly and rely on direct host status plus metric evidence.",
    ),
    tool_usage=(
        "Start with incident evidence_summary and agent_hints before calling tools.",
        "Use get_prometheus_range when you need to confirm duration, trend, or current persistence of absence.",
        "Use get_windows_events when you need crash, service-control-manager, or startup-failure evidence.",
        "Use get_windows_process_status when you need the current live state of the named process.",
        "Use get_windows_service_status only if the process is likely managed by a Windows service or related dependency.",
        "Use execute_powershell only when a specialized tool does not cover the needed read-only host check.",
        "Do not recommend remediation as fact unless at least one tool or incident evidence source supports the diagnosis.",
    ),
    allowed_tools=(
        "get_prometheus_range",
        "get_windows_events",
        "get_windows_process_status",
        "get_windows_service_status",
        "execute_powershell",
    ),
)


SERVICE_AVAILABILITY_SKILL = IncidentSkill(
    skill_id="service_availability",
    title="Service Availability",
    description=(
        "Use this skill when a Windows service is reported down or unavailable and the "
        "main task is to determine whether the service stopped, failed repeatedly, or "
        "is blocked by dependency or configuration issues."
    ),
    applies_when=(
        "Use when alert.name is ServiceDown.",
        "Use when scope.resource_type is service.",
        "Use when signal.category is availability and the affected workload is service-based.",
    ),
    investigation_steps=(
        "Confirm whether the service is stopped, starting, failed, or flapping.",
        "Check start mode and dependency chain before suggesting a restart.",
        "Look for Service Control Manager or application errors in the incident window.",
        "Distinguish between a service failure and a downstream dependency failure.",
    ),
    tool_usage=(
        "Start with incident evidence_summary and agent_hints before calling tools.",
        "Use get_windows_service_status as the primary live-state check for the named service.",
        "Use get_windows_events to gather Service Control Manager, application, and dependency failures.",
        "Use get_prometheus_range when you need to confirm the outage window or metric persistence.",
        "Use get_windows_process_status when the service has a known process name that needs live verification.",
        "Use execute_powershell only when a specialized tool does not cover the needed read-only host check.",
        "Do not move toward restart guidance until logs or host state support that recommendation.",
    ),
    allowed_tools=(
        "get_windows_service_status",
        "get_windows_events",
        "get_prometheus_range",
        "get_windows_process_status",
        "execute_powershell",
    ),
)


FALLBACK_SKILL = IncidentSkill(
    skill_id="generic_windows_triage",
    title="Generic Windows Triage",
    description=(
        "Use this fallback skill when the incident does not cleanly match a more specific "
        "skill or when labels are incomplete."
    ),
    applies_when=(
        "Use only when no specific availability skill is a better match.",
    ),
    investigation_steps=(
        "Restate what is known from the incident.",
        "Identify the highest-value missing evidence.",
        "Use only the minimum tools required to close the biggest evidence gap.",
    ),
    tool_usage=(
        "Start from incident evidence and agent_hints.",
        "Prefer the tool named in agent_hints.recommended_tools when one is present.",
        "Use execute_powershell only for guarded read-only host inspection when the other tools are insufficient.",
        "Explain why each tool is being used before relying on its result.",
    ),
    allowed_tools=(
        "get_prometheus_range",
        "get_windows_events",
        "get_windows_process_status",
        "get_windows_service_status",
        "execute_powershell",
    ),
)


def select_incident_skills(incident: dict[str, Any]) -> list[IncidentSkill]:
    """Return deterministic skill matches for the incident."""
    alert = incident.get("alert", {}) or {}
    scope = incident.get("scope", {}) or {}
    signal = incident.get("signal", {}) or {}

    alert_name = str(alert.get("name", "")).strip().lower()
    resource_type = str(scope.get("resource_type", "")).strip().lower()
    probable_cause = str(signal.get("probable_cause", "")).strip().lower()

    selected: list[IncidentSkill] = []

    if alert_name == "processdown" or resource_type == "process" or "process" in probable_cause:
        selected.append(PROCESS_AVAILABILITY_SKILL)

    if alert_name == "servicedown" or resource_type == "service":
        selected.append(SERVICE_AVAILABILITY_SKILL)

    if not selected:
        selected.append(FALLBACK_SKILL)

    return selected


def render_skill_section(skills: list[IncidentSkill]) -> str:
    """Render selected skill definitions for prompt injection."""
    lines: list[str] = []

    for skill in skills:
        lines.append(f"Skill: {skill.skill_id}")
        lines.append(f"Purpose: {skill.description}")
        lines.append("Use this skill when:")
        for item in skill.applies_when:
            lines.append(f"- {item}")
        lines.append("What to do:")
        for item in skill.investigation_steps:
            lines.append(f"- {item}")
        lines.append("When to use tools:")
        for item in skill.tool_usage:
            lines.append(f"- {item}")
        lines.append("Preferred tools:")
        for tool_name in skill.allowed_tools:
            lines.append(f"- {tool_name}")
        lines.append("")

    return "\n".join(lines).strip()
