# Params
$ConfigPath = "c:\Users\dogma\Projects\MAMcrawler\mamcrawler_tunnel_config.yml"
$CloudflaredPath = (Get-Command cloudflared).Source

if (-not $CloudflaredPath) {
    Write-Error "Cloudflared not found in PATH."
    exit 1
}

Write-Host "Installing Cloudflare Tunnel as a Service..."

# 1. Uninstall existing if any
cloudflared service uninstall *>$null

# 2. Install
cloudflared service install
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install service. Ensure you are running as Administrator."
    exit 1
}

# 3. Update ImagePath to use our config
$ServiceKey = "HKLM:\SYSTEM\CurrentControlSet\Services\cloudflared"
try {
    $CurrentPath = (Get-ItemProperty -Path $ServiceKey).ImagePath
    # We want to insert --config <path> before 'run'
    # Default is usually: "C:\...\cloudflared.exe" --no-autoupdate tunnel run
    # OR: "C:\...\cloudflared.exe" tunnel run
    
    # Let's construct it explicitly to be safe
    $NewPath = "`"$CloudflaredPath`" --no-autoupdate tunnel --config `"$ConfigPath`" run"
    
    Set-ItemProperty -Path $ServiceKey -Name "ImagePath" -Value $NewPath
    Write-Host "Updated Service Configuration to use: $ConfigPath"
}
catch {
    Write-Error "Failed to update registry. $_"
    exit 1
}

# 4. Start Service
Start-Service cloudflared
Write-Host "Cloudflare Tunnel Service Started!"
