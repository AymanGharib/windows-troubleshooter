param(
  [string]$AlloyExe = "",
  [string]$ConfigPath = "config/alloy/config.alloy",
  [switch]$Foreground
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$resolvedConfig = Join-Path $repoRoot $ConfigPath

if (!(Test-Path $resolvedConfig)) {
  Write-Error "Alloy config not found: $resolvedConfig"
  exit 1
}

function Find-AlloyExe {
  param([string]$RequestedPath)

  if ($RequestedPath) {
    if (Test-Path $RequestedPath) {
      return (Resolve-Path $RequestedPath).Path
    }
    Write-Error "Alloy executable not found at: $RequestedPath"
    exit 1
  }

  $candidates = @(
    (Join-Path $repoRoot "tools\alloy\alloy-windows-amd64.exe"),
    (Join-Path $repoRoot "tools\alloy\alloy.exe"),
    "$env:ProgramFiles\GrafanaLabs\Alloy\alloy.exe",
    "$env:ProgramFiles\GrafanaLabs\Alloy\alloy-windows-amd64.exe",
    "$env:ProgramFiles\alloy\alloy.exe",
    "$env:ProgramFiles\alloy\alloy-windows-amd64.exe"
  )

  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path $candidate)) {
      return (Resolve-Path $candidate).Path
    }
  }

  $fromPath = Get-Command alloy.exe -ErrorAction SilentlyContinue
  if ($fromPath) {
    return $fromPath.Source
  }

  Write-Error @"
Could not find alloy.exe.

Pass -AlloyExe explicitly, for example:
  powershell -ExecutionPolicy Bypass -File .\config\alloy\start-alloy-windows.ps1 -AlloyExe 'C:\tools\alloy\alloy.exe'
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

$alloyPath = Find-AlloyExe -RequestedPath $AlloyExe
$alloyLeaf = Split-Path -Leaf $alloyPath
$configText = Get-Content $resolvedConfig -Raw
$lokiPushUrl = ""

if ($alloyLeaf -match 'installer') {
  Write-Warning "The selected executable looks like an installer, not the Alloy runtime binary. Prefer the installed 'alloy.exe' path."
}

if ($configText -match 'url\s*=\s*"([^"]+)"') {
  $lokiPushUrl = $matches[1]
}

$dataDir = "C:\ProgramData\alloy"
if (!(Test-Path $dataDir)) {
  New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
}

$args = @(
  "run",
  $resolvedConfig
)

Write-Host "Alloy executable:  $alloyPath"
Write-Host "Alloy config:      $resolvedConfig"
Write-Host "Data directory:    $dataDir"

if ($lokiPushUrl) {
  $readyUrl = $lokiPushUrl -replace '/loki/api/v1/push$', '/ready'
  if (Test-LokiReady -Url $readyUrl) {
    Write-Host "Loki ready:        yes ($readyUrl)"
  } else {
    Write-Warning "Loki does not appear ready at $readyUrl. Alloy can still be started, but ingestion may fail."
  }
}

if ($Foreground) {
  Write-Host "Starting Alloy in the foreground. Press Ctrl+C to stop."
  & $alloyPath @args
  exit $LASTEXITCODE
}

$process = Start-Process -FilePath $alloyPath -ArgumentList $args -PassThru
Write-Host "Alloy started in background with PID $($process.Id)."
Write-Host "To stop it later:"
Write-Host "  Stop-Process -Id $($process.Id)"
