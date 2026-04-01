param(
  [string]$ApiBase = "http://localhost:8000",
  [string]$PayloadPath = "testdata/sample-alert.json"
)

if (!(Test-Path $PayloadPath)) {
  Write-Error "Payload not found: $PayloadPath"
  exit 1
}

$body = Get-Content $PayloadPath -Raw
Invoke-RestMethod -Uri "$ApiBase/test/correlate" -Method POST -ContentType "application/json" -Body $body
