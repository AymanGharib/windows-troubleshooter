# Incident Agent Design

## Goal

Turn the current RabbitMQ consumer plus `ClaudeAIAgent` into a Windows incident agent that investigates first, only remediates behind guardrails, and always verifies any action it takes.

## What We Have

- compact incident payloads from the correlator
- RabbitMQ delivery into the agent
- file-based prompt loading
- local MCP tool auto-discovery in `agent/app/tools`
- callback-based tool permission hooks

## What Is Still Wrong

- `agent/app/prompts/agent_system_prompt.txt` is still a test prompt
- prompt loading currently flattens multiline prompts into one line
- the consumer still expects the old generic JSON response shape
- there is no incident skill routing yet
- there is no remediation policy or verification loop yet

## Target Model

Use one agent with internal modes:

1. `triage`
2. `investigate`
3. `recommend`
4. `remediate`
5. `verify`
6. `complete`

Default behavior is `triage` and `investigate`. The agent must not enter `remediate` unless:

- probable cause is specific
- confidence is above threshold
- the alert type maps to an allowlisted runbook
- the action is low-risk
- prechecks passed

If any gate fails, the agent stops at recommendation-only output.

## Skill Routing

Use a hybrid approach:

1. deterministic preselection from incident metadata
2. optional model choice only from that shortlist

Route using:

- `alert.labels.alertname`
- `alert.labels.type`
- `assessment.category`
- `assessment.probable_cause`
- `data_gaps`

Initial skill packs:

1. `process_availability`
2. `service_availability`
3. `disk_capacity`
4. `host_resource_pressure`
5. `generic_windows_triage`

Each skill should define:

- matching rules
- preferred tools
- investigation checklist
- optional remediation runbooks
- verification steps
- minimum confidence for remediation

## MCP Tool Plan

### Read-only investigation tools

These should be available in normal investigation mode:

1. `query_prometheus_range`
2. `query_prometheus_instant`
3. `query_loki_logs`
4. `get_windows_service_status`
5. `get_windows_process_status`
6. `get_windows_disk_status`
7. `get_windows_eventlog_direct`

### Remediation tools

Do not expose a fully open shell first. Expose named runbooks:

1. `restart_windows_service`
2. `start_windows_service`
3. `stop_windows_service`
4. `restart_named_process_via_service`

### Verification tools

Verification should reuse the read-only tools:

1. recheck Prometheus
2. recheck service or process status
3. fetch post-action logs
4. confirm the alert is improving or resolved

## PowerShell Strategy

Do not lead with a general write-capable shell.

Use:

1. specialized MCP wrappers for common checks
2. one restricted read-only PowerShell tool
3. separate named remediation runbooks for write actions

The read-only PowerShell tool should allow query families like:

- `Get-Service`
- `Get-Process`
- `Get-CimInstance`
- `Get-WinEvent`
- `Test-NetConnection`
- `Get-Volume`

It should deny writes, downloads, service changes, process launches, deletes, and registry mutation.

## Logs and Metrics Strategy

Evidence order should be:

1. use incident evidence already attached by the correlator
2. if needed, query Loki for the same host and window
3. if Loki is missing or stale, query Windows Event Log directly
4. use Prometheus to confirm current state

This matters because recent incidents already show both:

- useful Windows event evidence
- `loki_unavailable:HTTPStatusError`

## Remediation Policy

Add an explicit policy object, not just prompt text.

Suggested fields:

- `enabled`
- `mode`
- `min_confidence`
- `allowed_alerts`
- `allowed_runbooks`
- `blocked_hosts`
- `requires_verification`
- `max_actions_per_incident`

Suggested initial mode:

- `recommend_only`

First auto-remediation candidate:

- restart a known Windows service for `ServiceDown`

Disk cleanup should remain recommendation-only at first.

## System Prompt

The prompt should become incident-native and mode-aware.

It should contain:

1. role
2. investigation-first rules
3. skill routing rules
4. tool usage rules
5. remediation gates
6. verification rules
7. strict output schema

Important: stop flattening prompts into one line in `agent/app/config.py`. The current normalization will make a serious operational prompt much weaker.

## Result Schema

Replace the old `status/message` response with something like:

```json
{
  "status": "COMPLETED",
  "mode": "investigate",
  "summary": "Alloy failed because port 12345 was already in use.",
  "incident_key": "5d553e185c2201442468f82f",
  "confidence": 0.82,
  "diagnosis": {
    "category": "availability",
    "probable_cause": "port_conflict_on_alloy_http_listener"
  },
  "evidence_used": [],
  "actions_taken": [],
  "recommended_actions": [],
  "verification": {
    "performed": false,
    "results": []
  },
  "needs_human": true
}
```

If remediation happens, `actions_taken` and `verification` should be required.

## Files To Add

```text
agent/app/agent/incident_prompt_builder.py
agent/app/agent/incident_skills.py
agent/app/agent/remediation_policy.py
agent/app/agent/result_schema.py
agent/app/prompts/incident_agent_system_prompt.txt
agent/app/tools/prometheus_tools.py
agent/app/tools/loki_tools.py
agent/app/tools/windows_read_tools.py
agent/app/tools/remediation_tools.py
```

## Recommended Build Order

1. preserve multiline prompts in `agent/app/config.py`
2. replace the test prompt
3. add deterministic routing for `ProcessDown` and `ServiceDown`
4. add read-only Prometheus, Loki, Windows service, and Windows process tools
5. update the consumer to parse the new result schema
6. add remediation policy and callback enforcement
7. add one safe runbook plus verification

## Best First Slice

Start with:

1. alert types: `ProcessDown` and `ServiceDown`
2. skills: `process_availability` and `service_availability`
3. tools:
   - `query_prometheus_range`
   - `query_loki_logs`
   - `get_windows_service_status`
   - `get_windows_process_status`
4. policy: `recommend_only`

That gives a useful investigation agent before we automate repairs.
