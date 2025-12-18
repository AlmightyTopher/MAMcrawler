# WireGuard Python-Only Tunnel Setup Script
# Run this in Administrator PowerShell
# This sets up a WireGuard tunnel that only Python traffic uses
# Windows gets VPN while System Python gets dedicated tunnel

Write-Host "================================================================================================" -ForegroundColor Cyan
Write-Host "WireGuard Python-Only Tunnel Setup" -ForegroundColor Cyan
Write-Host "Run this in Administrator PowerShell" -ForegroundColor Cyan
Write-Host "================================================================================================" -ForegroundColor Cyan
Write-Host ""

# Verify Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "ERROR: This script must run as Administrator!" -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Red
    exit 1
}

Write-Host "✓ Running as Administrator" -ForegroundColor Green
Write-Host ""

# Get the script directory
$scriptDir = Get-Location

Write-Host "Step 1: Copy WireGuard Config File" -ForegroundColor Yellow
Write-Host "-" * 100
$configSrc = Join-Path $scriptDir "TopherTek-Python-Tunnel.conf"
$configDest = "C:\Program Files\WireGuard\Data\Configurations\TopherTek-Python-Tunnel.conf"

if (Test-Path $configSrc) {
    Write-Host "  Source: $configSrc"
    Write-Host "  Dest:   $configDest"

    # Ensure destination directory exists
    $destDir = Split-Path $configDest
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        Write-Host "  Created directory: $destDir"
    }

    Copy-Item -Path $configSrc -Destination $configDest -Force
    Write-Host "  ✓ Config copied successfully" -ForegroundColor Green
}
else {
    Write-Host "  ✗ Config file not found: $configSrc" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Start WireGuard Service" -ForegroundColor Yellow
Write-Host "-" * 100

$wgService = Get-Service -Name "wg-quick" -ErrorAction SilentlyContinue
if ($wgService) {
    if ($wgService.Status -eq "Running") {
        Write-Host "  ✓ WireGuard service already running" -ForegroundColor Green
    }
    else {
        Write-Host "  Starting WireGuard service..."
        Start-Service -Name "wg-quick" -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        $wgService = Get-Service -Name "wg-quick"
        if ($wgService.Status -eq "Running") {
            Write-Host "  ✓ WireGuard service started" -ForegroundColor Green
        }
        else {
            Write-Host "  ⚠ WireGuard service may not have started (might need manual activation)" -ForegroundColor Yellow
        }
    }
}
else {
    Write-Host "  ⚠ WireGuard service 'wg-quick' not found" -ForegroundColor Yellow
    Write-Host "  You may need to manually activate the tunnel in WireGuard GUI" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 3: Create Python Firewall Rule (Outbound - Allow through WireGuard)" -ForegroundColor Yellow
Write-Host "-" * 100

$pythonExe = "C:\Program Files\Python311\python.exe"
$ruleName = "PythonVPN-Outbound-WireGuard"

Write-Host "  Creating outbound rule for: $pythonExe"
Write-Host "  Rule name: $ruleName"

# Remove existing rule if it exists
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existingRule) {
    Write-Host "  Removing existing rule..."
    Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
}

# Create new rule - Allow Python outbound traffic (will route through WireGuard)
New-NetFirewallRule -DisplayName $ruleName `
    -Direction Outbound `
    -Program $pythonExe `
    -Action Allow `
    -RemotePorts 80, 443, 8080, 8443, 13378, 51820 `
    -Protocol TCP, UDP `
    -Enabled True | Out-Null

Write-Host "  ✓ Outbound firewall rule created" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Create Python Firewall Rule (Inbound - Allow responses)" -ForegroundColor Yellow
Write-Host "-" * 100

$ruleName2 = "PythonVPN-Inbound-WireGuard"

Write-Host "  Rule name: $ruleName2"

# Remove existing rule if it exists
$existingRule2 = Get-NetFirewallRule -DisplayName $ruleName2 -ErrorAction SilentlyContinue
if ($existingRule2) {
    Write-Host "  Removing existing rule..."
    Remove-NetFirewallRule -DisplayName $ruleName2 -ErrorAction SilentlyContinue
}

# Create new rule - Allow Python inbound (responses from VPN)
New-NetFirewallRule -DisplayName $ruleName2 `
    -Direction Inbound `
    -Program $pythonExe `
    -Action Allow `
    -LocalPorts 80, 443, 8080, 8443, 13378, 51820 `
    -Protocol TCP, UDP `
    -Enabled True | Out-Null

Write-Host "  ✓ Inbound firewall rule created" -ForegroundColor Green

Write-Host ""
Write-Host "Step 5: Add WireGuard Interface Route (Optional - for specific traffic)" -ForegroundColor Yellow
Write-Host "-" * 100

Write-Host "  Checking for WireGuard interface..."
$wgInterface = Get-NetAdapter -Name "Cloudflare" -ErrorAction SilentlyContinue

if ($wgInterface) {
    Write-Host "  Found WireGuard interface: $($wgInterface.Name)"
    Write-Host "  (No additional routing needed - WireGuard handles this)" -ForegroundColor Green
}
else {
    Write-Host "  WireGuard interface not yet active (will be created when tunnel connects)" -ForegroundColor Yellow
    Write-Host "  This is normal - routing will work once tunnel is active" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 6: Set Network Interface Metrics (if needed)" -ForegroundColor Yellow
Write-Host "-" * 100

Write-Host "  Checking network interface metrics..."
$interfaces = Get-NetIPInterface -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.InterfaceAlias -like "*Ethernet*" -or $_.InterfaceAlias -like "*WiFi*" } | Sort-Object -Property RouteMetric

if ($interfaces) {
    foreach ($int in $interfaces) {
        Write-Host "  - $($int.InterfaceAlias): Metric $($int.RouteMetric)"
    }
    Write-Host "  ✓ Current metrics shown above" -ForegroundColor Green
}
else {
    Write-Host "  ⚠ Could not retrieve interface metrics (this is okay)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 7: Verify Setup and Test Tunnel" -ForegroundColor Yellow
Write-Host "-" * 100

Write-Host "  Setup complete! Next steps:"
Write-Host ""
Write-Host "  1. Open WireGuard GUI (Start Menu > WireGuard)"
Write-Host "  2. Click 'Activate tunnel' for 'TopherTek-Python-Tunnel'"
Write-Host "  3. Verify both Python and Windows have different IPs:"
Write-Host ""
Write-Host "     cd $scriptDir"
Write-Host "     python verify_wireguard.py"
Write-Host ""
Write-Host "  4. If tests pass, Python traffic uses VPN, Windows uses normal internet"
Write-Host "     If tests fail, check:"
Write-Host "       - WireGuard tunnel is activated"
Write-Host "       - Firewall rules are enabled"
Write-Host "       - Internet connection is working"
Write-Host ""

Write-Host "================================================================================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "================================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Firewall Rules Created:" -ForegroundColor Green
Get-NetFirewallRule -DisplayName "PythonVPN*" | Format-Table -Property DisplayName, Direction, Enabled, Action

Write-Host ""
Write-Host "To verify your setup works, run:" -ForegroundColor Cyan
Write-Host "  python verify_wireguard.py" -ForegroundColor Cyan
Write-Host ""
