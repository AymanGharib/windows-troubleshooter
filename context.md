# Project Context

## Current Goal

This repo is being shaped into an incident pipeline for Windows hosts:

1. Prometheus detects metric-based issues.
2. Alertmanager forwards alerts to the correlator.
3. The correlator enriches alerts with Prometheus/Loki context and emits compact incident events.
4. RabbitMQ carries those incidents to an agent service.
5. The agent will investigate first, and later may remediate with guardrails.

## Current Pipeline

### Metrics and Alerts

- `windows_exporter` is scraped by Prometheus via [`config/prometheus/prometheus.yml`](/c:/Users/ayman/os-layer/config/prometheus/prometheus.yml).
- Alert rules live in:
  - [`config/prometheus/rules/windows.yml`](/c:/Users/ayman/os-layer/config/prometheus/rules/windows.yml)
  - [`config/prometheus/rules/generated-processes.yml`](/c:/Users/ayman/os-layer/config/prometheus/rules/generated-processes.yml)
- Process-specific rules are generated from [`config/prometheus/render-process-rules.ps1`](/c:/Users/ayman/os-layer/config/prometheus/render-process-rules.ps1).
- For now, `host`, `job`, and `env` are intentionally hardcoded for the single-host setup.

### Logs

- Loki runs in Docker using [`config/loki/local-config.yaml`](/c:/Users/ayman/os-layer/config/loki/local-config.yaml).
- Windows Event Logs are ingested from the Windows host using Alloy, not Docker Promtail.
- The active Alloy config is [`config/alloy/config.alloy`](/c:/Users/ayman/os-layer/config/alloy/config.alloy).
- Helper scripts:
  - start Alloy: [`config/alloy/start-alloy-windows.ps1`](/c:/Users/ayman/os-layer/config/alloy/start-alloy-windows.ps1)
  - verify Loki ingestion: [`config/alloy/test-loki-windows-stream.ps1`](/c:/Users/ayman/os-layer/config/alloy/test-loki-windows-stream.ps1)
- This path is working: Loki now contains `windows-eventlog` streams for the configured host.

### Correlator

- FastAPI webhook entrypoint: [`correlator/app/main.py`](/c:/Users/ayman/os-layer/correlator/app/main.py)
- Correlation logic: [`correlator/app/engine.py`](/c:/Users/ayman/os-layer/correlator/app/engine.py)
- Models: [`correlator/app/models.py`](/c:/Users/ayman/os-layer/correlator/app/models.py)
- Publishers: [`correlator/app/publisher.py`](/c:/Users/ayman/os-layer/correlator/app/publisher.py)
- RabbitMQ topology helper: [`correlator/app/rabbitmq_init.py`](/c:/Users/ayman/os-layer/correlator/app/rabbitmq_init.py)

The correlator was refactored to emit a compact, agent-oriented incident schema instead of raw bulky evidence.

Important changes already made:

- Metric point series are compressed into summaries.
- Loki lines are parsed and cleaned into smaller log entries.
- The incident now includes a clear investigation window.
- The incident now includes compact `alert`, `scope`, `time`, `signal`, `evidence_summary`, and `agent_hints` sections.
- The correlator can publish either to file output or to RabbitMQ.

### RabbitMQ

- RabbitMQ is now part of [`docker-compose.yml`](/c:/Users/ayman/os-layer/docker-compose.yml).
- Current incident topology:
  - exchange: `incidents.topic`
  - exchange type: `topic`
  - queue: `agent.incidents.tasks`
  - routing key: `incidents.correlator.enriched`
- Root env values are in [`.env`](/c:/Users/ayman/os-layer/.env).

### Agent

- Agent framework lives under [`agent/app`](/c:/Users/ayman/os-layer/agent/app).
- RabbitMQ startup entrypoint: [`agent/app/__main__.py`](/c:/Users/ayman/os-layer/agent/app/__main__.py)
- Incident consumer: [`agent/app/rabbitmq/consumer.py`](/c:/Users/ayman/os-layer/agent/app/rabbitmq/consumer.py)
- Local RabbitMQ result publisher: [`agent/app/rabbitmq/publisher.py`](/c:/Users/ayman/os-layer/agent/app/rabbitmq/publisher.py)
- RabbitMQ env config: [`agent/app/configs/environment_vars/rabbitmq_settings.py`](/c:/Users/ayman/os-layer/agent/app/configs/environment_vars/rabbitmq_settings.py)

The consumer has been adapted so it now:

- listens to the incident queue instead of the old ticket queue
- declares and binds to the same exchange/routing key as the correlator
- receives compact incident payloads
- logs incident metadata such as alert name, host, resource type, and resource name
- forwards progress/status updates to `agent.results`

See the current target design here:

- [`agent/AGENT_DESIGN.md`](/c:/Users/ayman/os-layer/agent/AGENT_DESIGN.md)

## What Works Now

- Prometheus rules can monitor named watched processes using generated per-process rules.
- Loki ingestion from Windows via Alloy is working.
- The correlator can attach Loki evidence when relevant.
- The correlator emits a much smaller incident payload that is more suitable for downstream agents.
- RabbitMQ is present in Docker Compose.
- The correlator can publish incidents into RabbitMQ.
- The agent consumer is now wired to the same RabbitMQ incident queue and exchange.

## Known Intentional Shortcuts

- `host`, `job`, and `env` are still hardcoded in several places for the current single-host setup.
- The current agent framework still reflects earlier ADO-oriented assumptions in prompts and broader behavior, even though the RabbitMQ consumer has been moved toward incident handling.
- The downstream agent design is not finished yet:
  - MCP tools are not implemented yet
  - PowerShell execution strategy is not implemented yet
  - troubleshooter/remediator behavior is not implemented yet
  - skill/prompt routing is not implemented yet

## Known Gaps / Next Work

### Agent Design

The intended direction is:

- one incident agent
- troubleshooting-first behavior
- optional remediation escalation when confidence is high and the action is low-risk
- MCP tools for logs, metrics, and system inspection
- later, constrained remediation tools and verification loops

### Tooling Still Needed

Planned MCP/tooling areas:

- fetch Windows events from Loki
- fetch Prometheus ranges
- readonly PowerShell execution
- targeted remediation actions
- verification checks after remediation

### Evidence Quality

The event shape is much better now, but evidence selection still needs tuning:

- some Loki hits are still low-signal or unrelated
- `data_gaps` behavior may need softening in some alert types
- further log relevance filtering will likely be needed

## How To Run

### Start infrastructure

From repo root:

```powershell
docker compose up -d rabbitmq prometheus alertmanager loki
```

### Run Alloy on Windows host

```powershell
powershell -ExecutionPolicy Bypass -File .\config\alloy\start-alloy-windows.ps1 -AlloyExe 'C:\Program Files\GrafanaLabs\Alloy\alloy-windows-amd64.exe'
```

### Run correlator

Use RabbitMQ output mode when ready to send incidents downstream.

### Run agent consumer

From the `agent` folder:

```powershell
python -m app
```

## Important Files

- Root env: [`.env`](/c:/Users/ayman/os-layer/.env)
- Compose: [`docker-compose.yml`](/c:/Users/ayman/os-layer/docker-compose.yml)
- Correlator engine: [`correlator/app/engine.py`](/c:/Users/ayman/os-layer/correlator/app/engine.py)
- Correlator publisher: [`correlator/app/publisher.py`](/c:/Users/ayman/os-layer/correlator/app/publisher.py)
- Agent consumer: [`agent/app/rabbitmq/consumer.py`](/c:/Users/ayman/os-layer/agent/app/rabbitmq/consumer.py)
- Agent startup: [`agent/app/__main__.py`](/c:/Users/ayman/os-layer/agent/app/__main__.py)

## Suggested Immediate Next Step

Implement the first minimal incident-native slice:

1. preserve multiline prompts
2. replace the test prompt
3. add deterministic skill routing for `ProcessDown` and `ServiceDown`
4. add read-only MCP tools for Prometheus, Loki, Windows service status, and Windows process status
