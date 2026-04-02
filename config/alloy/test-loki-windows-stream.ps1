param(
  [string]$LokiBaseUrl = "http://localhost:3100",
  [string]$HostLabel = "my-desktop",
  [int]$Limit = 5,
  [int]$TimeoutSec = 10,
  [int]$LookbackHours = 6
)

$query = "{job=""windows-eventlog"",host=""$HostLabel""}"
$encodedQuery = [uri]::EscapeDataString($query)
$endNs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() * 1000000
$startNs = [DateTimeOffset]::UtcNow.AddHours(-1 * $LookbackHours).ToUnixTimeMilliseconds() * 1000000
$uri = "$LokiBaseUrl/loki/api/v1/query_range?query=$encodedQuery&limit=$Limit&direction=BACKWARD&start=$startNs&end=$endNs"

try {
  $response = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec $TimeoutSec
} catch {
  Write-Error "Failed to query Loki: $($_.Exception.Message)"
  exit 1
}

$streams = @($response.data.result)
$count = $streams.Count

Write-Host "Query: $query"
Write-Host "Streams found: $count"

if ($count -eq 0) {
  Write-Warning "No windows-eventlog streams found for host '$HostLabel'. Alloy may not be running yet, or no events have been ingested."
  exit 0
}

foreach ($stream in $streams) {
  $labels = $stream.stream | ConvertTo-Json -Compress
  Write-Host ""
  Write-Host "Stream labels: $labels"
  foreach ($entry in ($stream.values | Select-Object -First 3)) {
    Write-Host "  $($entry[1])"
  }
}
