# Setup WireGuard Python Tunnel
$ErrorActionPreference = "Stop"

# 1. Start the Tunnel Service
Write-Host "Starting WireGuard Tunnel Service..."
$wgPath = "C:\Program Files\WireGuard\wireguard.exe"
$tunnelName = "TopherTek-Python-Tunnel"
$serviceName = "WireGuardTunnel$tunnelName"

# Try starting via wireguard.exe as requested
Start-Process -FilePath $wgPath -ArgumentList "/tunnelservice", $tunnelName -Wait -NoNewWindow

# Wait for service to be running
$retries = 5
while ($retries -gt 0) {
    $svc = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq 'Running') {
        Write-Host "Service is RUNNING."
        break
    }
    Write-Host "Waiting for service... ($retries)"
    Start-Sleep -Seconds 2
    $retries--
}

# Wait for interface to come up
Start-Sleep -Seconds 3

# 2. Get Interface Index
$interface = Get-NetIPInterface | Where-Object { $_.InterfaceAlias -like "*TopherTek*" }
if (-not $interface) {
    Write-Error "Could not find WireGuard interface 'TopherTek-Python-Tunnel'"
}
$index = $interface.ifIndex
Write-Host "Found Interface Index: $index"

# 3. Lower Interface Metric (Prefer WAN)
Write-Host "Setting Interface Metric to 500..."
Set-NetIPInterface -InterfaceIndex $index -InterfaceMetric 500

# 4. Create Firewall Rule for Python
$pythonPath = (Get-Command python.exe).Source
Write-Host "Detected Python Path: $pythonPath"

$ruleName = "PythonVPN"
# Remove existing rule if it exists
Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

Write-Host "Creating Firewall Rule..."
New-NetFirewallRule -DisplayName $ruleName -Program $pythonPath -Direction Outbound -Action Allow -Profile Any

# 5. Bind Firewall Rule to WireGuard Interface
Write-Host "Binding Firewall Rule to WireGuard Interface..."
Set-NetFirewallRule -DisplayName $ruleName -InterfaceAlias "TopherTek-Python-Tunnel"

# 6. Add Route for Python Traffic
# Note: This adds a default route to the VPN table, but since we set metric 500, 
# the system default route (metric < 500) should still be preferred for non-bound apps.
# However, the user asked to "Add a route for Python's traffic". 
# The firewall rule binds the application to the interface, forcing it to use that interface's routes.
# We need to ensure the interface has a route to 0.0.0.0/0.
Write-Host "Adding Default Route to VPN Interface..."
try {
    New-NetRoute -DestinationPrefix 0.0.0.0/0 -InterfaceIndex $index -PolicyStore PersistentStore -NextHop 0.0.0.0 -ErrorAction SilentlyContinue
}
catch {
    Write-Host "Route might already exist: $_"
}

# Verification
Write-Host "`n--- VERIFICATION ---"
Write-Host "Interface Status:"
Get-NetIPInterface -InterfaceIndex $index | Select-Object InterfaceAlias, InterfaceMetric, ConnectionState

Write-Host "`nFirewall Rule:"
Get-NetFirewallRule -DisplayName $ruleName | Select-Object DisplayName, InterfaceAlias

Write-Host "`nRoute Table (VPN Interface):"
Get-NetRoute -InterfaceIndex $index | Where-Object { $_.DestinationPrefix -eq "0.0.0.0/0" }

Write-Host "`nSetup Complete."
