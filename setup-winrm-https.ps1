param(
    [string]$TargetHost = $env:COMPUTERNAME,
    [int]$Port = 5986
)

$ErrorActionPreference = "Continue"

function Write-Check($name, $ok, $details) {
    $status = if ($ok) { "OK" } else { "FAIL" }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host "[$status] $name" -ForegroundColor $color
    if ($details) { Write-Host "       $details" }
}

Write-Host "=== WinRM HTTPS Diagnostics ==="
Write-Host "TargetHost: $TargetHost  Port: $Port"
Write-Host ""

# 1) Admin check
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
Write-Check "Running as Administrator" $isAdmin $(if (-not $isAdmin) { "Rerun in elevated PowerShell." })

# 2) Network profiles
$profiles = Get-NetConnectionProfile -ErrorAction SilentlyContinue
$publicProfiles = @($profiles | Where-Object { $_.NetworkCategory -eq "Public" })

Write-Check "Network profiles are not Public" ($publicProfiles.Count -eq 0) $(
    if ($publicProfiles.Count -gt 0) {
        "Public profiles: " + (($publicProfiles | ForEach-Object { "$($_.InterfaceAlias)($($_.Name))" } | Sort-Object) -join ", ")
    } else {
        ""
    }
)

# 3) WinRM service
$svc = Get-Service WinRM -ErrorAction SilentlyContinue
$svcOk = $svc -and $svc.Status -eq "Running"
Write-Check "WinRM service running" $svcOk $(
    if ($svc) {
        "Status=$($svc.Status), StartType=$((Get-CimInstance Win32_Service -Filter "Name='WinRM'").StartMode)"
    } else {
        "Service missing"
    }
)

# 4) Listeners
$listenersText = & winrm enumerate winrm/config/listener 2>&1
$hasHttps = ($listenersText -match "Transport = HTTPS") -and ($listenersText -match "Port = $Port")
Write-Check "HTTPS listener exists on port $Port" $hasHttps $(
    if (-not $hasHttps) { "Run setup script to create HTTPS listener." } else { "" }
)

Write-Host ""
Write-Host "Listener dump:"
Write-Host $listenersText
Write-Host ""

# 5) Extract cert thumbprint from HTTPS listener
$thumbprint = $null
$lines = $listenersText -split "`r?`n"

for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "Transport = HTTPS") {
        for ($j = $i; $j -lt [Math]::Min($i + 20, $lines.Count); $j++) {
            if ($lines[$j] -match "CertificateThumbprint\s*=\s*([A-Fa-f0-9]+)") {
                $thumbprint = $matches[1].ToUpper()
                break
            }
        }
        if ($thumbprint) { break }
    }
}

if ($thumbprint) {
    $cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Thumbprint -eq $thumbprint }
    if ($cert) {
        $sanExt = $cert.Extensions | Where-Object { $_.Oid.FriendlyName -eq "Subject Alternative Name" }
        $sanText = if ($sanExt) { $sanExt.Format($true) } else { "No SAN extension found." }
        $notExpired = $cert.NotAfter -gt (Get-Date)

        Write-Check "HTTPS listener certificate found" $true "Thumbprint=$thumbprint"
        Write-Check "Certificate not expired" $notExpired "NotBefore=$($cert.NotBefore) NotAfter=$($cert.NotAfter)"
        Write-Host "       Subject: $($cert.Subject)"
        Write-Host "       SAN: $sanText"
    } else {
        Write-Check "HTTPS listener certificate found" $false "Thumbprint=$thumbprint not found in LocalMachine\My"
    }
} else {
    Write-Check "HTTPS listener certificate found" $false "Could not parse CertificateThumbprint from listener output."
}

# 6) Firewall rule
$fwRules = Get-NetFirewallRule -Enabled True -Direction Inbound -Action Allow -ErrorAction SilentlyContinue |
    Get-NetFirewallPortFilter -ErrorAction SilentlyContinue |
    Where-Object { $_.Protocol -eq "TCP" -and $_.LocalPort -eq "$Port" }

Write-Check "Inbound firewall allows TCP $Port" ($fwRules.Count -gt 0) $(
    if ($fwRules.Count -eq 0) { "Create/enable firewall rule for WinRM HTTPS." } else { "" }
)

# 7) Connectivity test
try {
    $null = Test-WSMan -ComputerName $TargetHost -UseSSL -Port $Port -ErrorAction Stop
    Write-Check "Test-WSMan -UseSSL succeeds" $true ""
}
catch {
    $msg = $_.Exception.Message
    Write-Check "Test-WSMan -UseSSL succeeds" $false $msg

    if ($msg -match "unknown certificate authority") {
        Write-Host "       Hint: Trust issue. For dev, disable cert verification in client; for prod, import cert/CA."
    }

    if ($msg -match "common name \(CN\) that does not match") {
        Write-Host "       Hint: Recreate cert with SAN/CN including target host ($TargetHost, host.docker.internal, localhost)."
    }
}

# 8) Local port listening check
$tcp = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
Write-Check "Port $Port is listening" ($null -ne $tcp) $(
    if ($tcp) {
        "Listening on " + (($tcp.LocalAddress | Sort-Object -Unique) -join ", ")
    } else {
        "Not listening"
    }
)

Write-Host ""
Write-Host "=== Done ==="
Write-Host "If FAIL remains on cert trust/name, regenerate cert with SANs and rebind WinRM listener."