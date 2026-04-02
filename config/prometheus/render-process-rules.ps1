param(
  [string]$EnvPath = ".env",
  [string]$OutputPath = "config/prometheus/rules/generated-processes.yml",
  [string]$HostLabel = "my-desktop",
  [string]$JobLabel = "windows-desktop",
  [string]$EnvLabel = "dev"
)

function Get-DotEnvValue {
  param(
    [string[]]$Lines,
    [string]$Key
  )

  foreach ($line in $Lines) {
    if ($line -match "^\s*$Key=(.*)$") {
      return $matches[1].Trim()
    }
  }

  return ""
}

function Get-ProcessList {
  param([string[]]$Lines)

  $namesRaw = Get-DotEnvValue -Lines $Lines -Key "WATCHED_PROCESS_NAMES"
  if ($namesRaw) {
    return $namesRaw.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ }
  }

  $regexRaw = Get-DotEnvValue -Lines $Lines -Key "WATCHED_PROCESS_REGEX"
  if (-not $regexRaw) {
    return @()
  }

  $cleaned = $regexRaw.Replace("(?i)", "")
  return $cleaned.Split("|") | ForEach-Object { $_.Trim() } | Where-Object { $_ }
}

function Get-RegexEscapedValue {
  param([string]$Value)

  return [regex]::Escape($Value)
}

if (!(Test-Path $EnvPath)) {
  Write-Error "Env file not found: $EnvPath"
  exit 1
}

$lines = Get-Content $EnvPath
$processes = @(Get-ProcessList -Lines $lines)

if ($processes.Count -eq 0) {
  Write-Error "No watched processes found in WATCHED_PROCESS_NAMES or WATCHED_PROCESS_REGEX"
  exit 1
}

$rules = @()
$rules += "groups:"
$rules += ""
$rules += "  - name: windows_processes"
$rules += "    rules:"

foreach ($process in $processes) {
  $escapedProcess = $process.Replace('"', '\"')
  $regexProcess = Get-RegexEscapedValue -Value $process
  $summaryPrefix = $process.Replace('"', '\"')

  $rules += ""
  $rules += "      - alert: ProcessDown"
  $rules += "        expr: |"
  $rules += "          absent_over_time(windows_process_cpu_time_total{"
  $rules += "            mode=""user"","
  $rules += "            process=~""(?i)^$regexProcess$"""
  $rules += "          }[1m])"
  $rules += "        for: 30s"
  $rules += "        labels:"
  $rules += "          severity: critical"
  $rules += "          type: process"
  $rules += "          process: $escapedProcess"
  $rules += "          host: $HostLabel"
  $rules += "          job: $JobLabel"
  $rules += "          env: $EnvLabel"
  $rules += "        annotations:"
  $rules += "          summary: ""$summaryPrefix process is missing"""

  $rules += ""
  $rules += "      - alert: ProcessHighCPU"
  $rules += "        expr: |"
  $rules += "          rate(windows_process_cpu_time_total{"
  $rules += "            mode=""user"","
  $rules += "            process=~""(?i)^$regexProcess$"""
  $rules += "          }[2m]) * 100 > 60"
  $rules += "        for: 3m"
  $rules += "        labels:"
  $rules += "          severity: warning"
  $rules += "          type: process_cpu"
  $rules += "          process: $escapedProcess"
  $rules += "          host: $HostLabel"
  $rules += "          job: $JobLabel"
  $rules += "          env: $EnvLabel"
  $rules += "        annotations:"
  $rules += "          summary: ""Process $escapedProcess using >60% CPU"""

  $rules += ""
  $rules += "      - alert: ProcessHighMemory"
  $rules += "        expr: |"
  $rules += "          windows_process_working_set_bytes{"
  $rules += "            process=~""(?i)^$regexProcess$"""
  $rules += "          } > 1073741824"
  $rules += "        for: 3m"
  $rules += "        labels:"
  $rules += "          severity: warning"
  $rules += "          type: process_memory"
  $rules += "          process: $escapedProcess"
  $rules += "          host: $HostLabel"
  $rules += "          job: $JobLabel"
  $rules += "          env: $EnvLabel"
  $rules += "        annotations:"
  $rules += "          summary: ""Process $escapedProcess using >1GB RAM"""
}

$dir = Split-Path -Parent $OutputPath
if ($dir -and !(Test-Path $dir)) {
  New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

Set-Content -Path $OutputPath -Value $rules -Encoding utf8
Write-Host "Generated $OutputPath for processes: $($processes -join ', ')"
