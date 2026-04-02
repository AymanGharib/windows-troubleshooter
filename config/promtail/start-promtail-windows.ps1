param(
  [string]$PromtailExe = "",
  [string]$ConfigPath = "config/promtail/promtail-windows.yml",
  [switch]$Foreground
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$resolvedConfig = Join-Path $repoRoot $ConfigPath

if (!(Test-Path $resolvedConfig)) {
  Write-Error "Promtail config not found: $resolvedConfig"
  exit 1
}

function Find-PromtailExe {
  param([string]$RequestedPath)

  if ($RequestedPath) {
    if (Test-Path $RequestedPath) {
      return (Resolve-Path $RequestedPath).Path
    }
    Write-Error "Promtail executable not found at: $RequestedPath"
    exit 1
  }

  $candidates = @(
    (Join-Path $repoRoot "tools\promtail\promtail-windows-amd64.exe"),
    (Join-Path $repoRoot "tools\promtail\promtail.exe"),
    "$env:ProgramFiles\promtail\promtail-windows-amd64.exe",
    "$env:ProgramFiles\promtail\promtail.exe",
    "$env:ProgramFiles\GrafanaLabs\promtail\promtail-windows-amd64.exe",
    "$env:ProgramFiles\GrafanaLabs\promtail\promtail.exe"
  )

  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path $candidate)) {
      return (Resolve-Path $candidate).Path
    }
  }

  $fromPath = Get-Command promtail.exe -ErrorAction SilentlyContinue
  if ($fromPath) {
    return $fromPath.Source
  }

  Write-Error @"
Could not find promtail.exe.

Pass -PromtailExe explicitly, for example:
  powershell -ExecutionPolicy Bypass -File .\config\promtail\start-promtail-windows.ps1 -PromtailExe 'C:\tools\promtail\promtail-windows-amd64.exe'
"@
  exit 1
}

function Test-LokiReady {
  param([string]$Url)

  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
    return $response.StatusCode -eq 200
  } catch {
    return $false
  }
}

$promtailPath = Find-PromtailExe -RequestedPath $PromtailExe
$configText = Get-Content $resolvedConfig -Raw
$lokiPushUrl = ""

if ($configText -match 'url:\s*(\S+)') {
  $lokiPushUrl = $matches[1]
}

$positionsPath = "C:\ProgramData\promtail\positions.yaml"
$bookmarkSystem = "C:\ProgramData\promtail\bookmark-system.xml"
$bookmarkApplication = "C:\ProgramData\promtail\bookmark-application.xml"
$dataDir = Split-Path -Parent $positionsPath

if (!(Test-Path $dataDir)) {
  New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
}

$args = @(
  "-config.file=$resolvedConfig"
)

Write-Host "Promtail executable: $promtailPath"
Write-Host "Promtail config:      $resolvedConfig"
Write-Host "Positions file:       $positionsPath"
Write-Host "Bookmark files:       $bookmarkSystem , $bookmarkApplication"

if ($lokiPushUrl) {
  $readyUrl = $lokiPushUrl -replace '/loki/api/v1/push$', '/ready'
  if (Test-LokiReady -Url $readyUrl) {
    Write-Host "Loki ready:           yes ($readyUrl)"
  } else {
    Write-Warning "Loki does not appear ready at $readyUrl. Promtail can still be started, but ingestion may fail."
  }
}

if ($Foreground) {
  Write-Host "Starting Promtail in the foreground. Press Ctrl+C to stop."
  & $promtailPath @args
  exit $LASTEXITCODE
}

$process = Start-Process -FilePath $promtailPath -ArgumentList $args -PassThru
Write-Host "Promtail started in background with PID $($process.Id)."
Write-Host "To stop it later:"
Write-Host "  Stop-Process -Id $($process.Id)"
