# VPN Port Proxy Setup for qBittorrent
# Run this as Administrator

Write-Host "================================" -ForegroundColor Green
Write-Host "VPN Port Proxy Setup" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Please right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "Running as Administrator: OK" -ForegroundColor Green
Write-Host ""

# Step 1: Remove any existing proxies on port 1080
Write-Host "[1] Cleaning up existing proxy configurations..." -ForegroundColor Cyan
$existingProxy = netsh interface portproxy show all | Select-String "1080"
if ($existingProxy) {
    Write-Host "Found existing proxy on port 1080, removing..." -ForegroundColor Yellow
    netsh interface portproxy delete v4tov4 listenport=1080 listenaddress=127.0.0.1
    Start-Sleep -Seconds 2
}

# Step 2: Create new port proxy
Write-Host "[2] Creating new port proxy (127.0.0.1:1080 -> 10.2.0.1:8080)..." -ForegroundColor Cyan
netsh interface portproxy add v4tov4 listenport=1080 listenaddress=127.0.0.1 connectport=8080 connectaddress=10.2.0.1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Port proxy created successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to create port proxy" -ForegroundColor Red
    exit 1
}

Start-Sleep -Seconds 2

# Step 3: Verify proxy was created
Write-Host "[3] Verifying port proxy configuration..." -ForegroundColor Cyan
$proxyInfo = netsh interface portproxy show all | Select-String "1080"
if ($proxyInfo) {
    Write-Host "✅ Proxy verified:" -ForegroundColor Green
    Write-Host $proxyInfo -ForegroundColor White
} else {
    Write-Host "❌ Failed to verify proxy" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "Next Steps:" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Configure qBittorrent:" -ForegroundColor Yellow
Write-Host "  1. Open qBittorrent" -ForegroundColor White
Write-Host "  2. Tools > Options > Network" -ForegroundColor White
Write-Host "  3. Proxy Server:" -ForegroundColor White
Write-Host "     - Type: SOCKS5" -ForegroundColor Cyan
Write-Host "     - IP Address: 127.0.0.1" -ForegroundColor Cyan
Write-Host "     - Port: 1080" -ForegroundColor Cyan
Write-Host "  4. Check: 'Use proxy for peer connections'" -ForegroundColor White
Write-Host "  5. Click OK" -ForegroundColor White
Write-Host ""
Write-Host "Test Connection:" -ForegroundColor Yellow
Write-Host "  Run: python check_vpn_connection.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "================================" -ForegroundColor Green
