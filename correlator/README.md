# OS Correlation Engine

FastAPI service that receives Alertmanager webhooks, correlates Prometheus metrics with Loki logs, and emits an enriched incident JSON for downstream AI agents.

## Endpoints

- `GET /health` - service health.
- `POST /alert` - Alertmanager webhook receiver.

## Environment Variables

- `PROMETHEUS_BASE_URL` (default `http://localhost:9090`)
- `LOKI_BASE_URL` (default `http://localhost:3100`)
- `WATCHED_PROCESS_REGEX` (default `(?i)wordpad|write`)
- `WATCHED_PROCESS_NAMES` (optional comma-separated process whitelist, used by the Prometheus rule generator)
- `DEFAULT_LOOKBACK_SECONDS` (default `300`)
- `MAX_LOGS_PER_EVENT` (default `30`)
- `MAX_METRIC_POINTS_PER_SERIES` (default `120`)
- `DEBUG_INCLUDE_QUERY_OUTPUT` (default `false`)
- `DEBUG_MAX_CHARS_PER_PAYLOAD` (default `4000`)
- `OUTPUT_MODE` (`stdout`, `file`, or `noop`)
- `OUTPUT_FILE_PATH` (default `output/incidents.jsonl`, used when `OUTPUT_MODE=file`)

## Run

```powershell
cd correlator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Alertmanager webhook in this repo already points to:

`http://host.docker.internal:8000/alert`

## Local Testing

Use the direct test endpoint (no Alertmanager required):

```powershell
cd correlator
powershell -ExecutionPolicy Bypass -File .\scripts\send-test-alert.ps1
```

This posts [sample-alert.json](./testdata/sample-alert.json) to:

`POST /test/correlate`

## Log Enriched JSON To File

Run with file output mode:

```powershell
cd correlator
$env:OUTPUT_MODE="file"
$env:OUTPUT_FILE_PATH="output/incidents.jsonl"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Each correlated event is appended as one JSON line in:

`correlator/output/incidents.jsonl`

## Process Whitelist Monitoring

The correlator does not create alerts on its own. The flow is:

1. Prometheus evaluates alert rules.
2. Alertmanager sends matching alerts to `POST /alert`.
3. The correlator enriches the alert with Prometheus and Loki evidence.

If you want adding a process to the whitelist to create dedicated alerts for that specific process, generate per-process Prometheus rules from `.env`:

```powershell
powershell -ExecutionPolicy Bypass -File .\config\prometheus\render-process-rules.ps1
```

This reads `WATCHED_PROCESS_NAMES` first, then falls back to names parsed from `WATCHED_PROCESS_REGEX`, and writes:

`config/prometheus/rules/generated-processes.yml`

After regenerating the file, reload or restart Prometheus so the new rules are picked up.

## Debug Query Output

Enable debug mode to include Prometheus/Loki query strings and raw (truncated) responses in each event:

```powershell
$env:DEBUG_INCLUDE_QUERY_OUTPUT="true"
$env:DEBUG_MAX_CHARS_PER_PAYLOAD="8000"
```

## Windows Alloy

To feed Windows Event Logs into Loki, run Grafana Alloy on the Windows host:

```powershell
powershell -ExecutionPolicy Bypass -File .\config\alloy\start-alloy-windows.ps1 -AlloyExe 'C:\path\to\alloy.exe'
```

The Alloy config keeps the labels compatible with the correlator:

- `job="windows-eventlog"`
- `host="my-desktop"`
- `channel="System"` or `channel="Application"`

To verify Loki is receiving the Windows stream:

```powershell
powershell -ExecutionPolicy Bypass -File .\config\alloy\test-loki-windows-stream.ps1
```
