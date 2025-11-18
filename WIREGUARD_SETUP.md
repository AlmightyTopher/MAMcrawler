# WireGuard Python-Only Tunnel Setup

## Quick Start (Administrator PowerShell Required)

**You have 2 options:**

### Option A: One-Step Automated Install (Recommended)
```powershell
# Run this ONE command as Administrator:
powershell -ExecutionPolicy Bypass -File install_wireguard_tunnel.ps1
```

### Option B: Manual Step-by-Step
Follow the steps below if automated install fails.

---

## Manual Setup Steps

### Prerequisites
1. WireGuard must be installed: https://www.wireguard.com/install/
2. Open PowerShell as Administrator

### Step 1: Copy Config File
```powershell
Copy-Item TopherTek-Python-Tunnel.conf C:\ProgramData\WireGuard\
```

### Step 2: Install Tunnel Service
```powershell
cd "C:\Program Files\WireGuard"
.\wireguard.exe /installtunnelservice "C:\ProgramData\WireGuard\TopherTek-Python-Tunnel.conf"
```

###Step 3: Start Tunnel
```powershell
.\wireguard.exe /tunnelservice TopherTek-Python-Tunnel
```

Wait 5 seconds, then verify:
```powershell
Get-Service | Where-Object {$_.DisplayName -like "*TopherTek*"}
```

Should show: **Running**

### Step 4: Get Interface Index
```powershell
$interface = Get-NetIPInterface | Where-Object {$_.InterfaceAlias -like "*TopherTek*"}
$interface
```

Note the **ifIndex** number (example: 23)

### Step 5: Lower Interface Metric
```powershell
# Replace XX with your ifIndex from Step 4
Set-NetIPInterface -InterfaceIndex XX -InterfaceMetric 500
```

### Step 6: Create Firewall Rules
```powershell
# System Python
New-NetFirewallRule -DisplayName "PythonVPN-System" `
    -Program "C:\Program Files\Python311\python.exe" `
    -Direction Outbound `
    -Action Allow `
    -Profile Any `
    -InterfaceAlias "TopherTek-Python-Tunnel"

# venv Python
New-NetFirewallRule -DisplayName "PythonVPN-venv" `
    -Program "C:\Users\dogma\Projects\MAMcrawler\venv\Scripts\python.exe" `
    -Direction Outbound `
    -Action Allow `
    -Profile Any `
    -InterfaceAlias "TopherTek-Python-Tunnel"
```

### Step 7: Add Route
```powershell
# Replace XX with your ifIndex
New-NetRoute -DestinationPrefix "0.0.0.0/0" `
    -InterfaceIndex XX `
    -PolicyStore PersistentStore `
    -NextHop "0.0.0.0"
```

### Step 8: Verify Setup
```powershell
python verify_wireguard.py
```

Should show TWO DIFFERENT IPs!

---

## Verification Commands

### Check Service Status
```powershell
Get-Service | Where-Object {$_.DisplayName -like "*TopherTek*"}
```

### Check Interface
```powershell
Get-NetIPInterface | Where-Object {$_.InterfaceAlias -like "*TopherTek*"}
```

### Check Firewall Rules
```powershell
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "PythonVPN*"}
```

### Check Routes
```powershell
Get-NetRoute -InterfaceAlias "TopherTek-Python-Tunnel"
```

---

## Troubleshooting

### "Service not found"
- Check WireGuard is installed: `Test-Path "C:\Program Files\WireGuard\wireguard.exe"`
- Config file in correct location: `Test-Path "C:\ProgramData\WireGuard\TopherTek-Python-Tunnel.conf"`

### "Interface not found"
- Wait 10 seconds after starting service
- Restart service: `Restart-Service WireGuardTunnel$TopherTek-Python-Tunnel`

### "Both Python use same IP"
- Verify firewall rules exist: `Get-NetFirewallRule | Where-Object {$_.DisplayName -like "PythonVPN*"}`
- Check interface metric is 500: `Get-NetIPInterface | Where-Object {$_.InterfaceAlias -like "*TopherTek*"}`
- Restart Python processes

---

## Uninstall

```powershell
# Stop service
$svc = Get-Service | Where-Object {$_.DisplayName -like "*TopherTek*"}
Stop-Service $svc.Name -Force

# Remove firewall rules
Remove-NetFirewallRule -DisplayName "PythonVPN-System"
Remove-NetFirewallRule -DisplayName "PythonVPN-venv"

# Uninstall service
cd "C:\Program Files\WireGuard"
.\wireguard.exe /uninstalltunnelservice TopherTek-Python-Tunnel

# Remove config
Remove-Item "C:\ProgramData\WireGuard\TopherTek-Python-Tunnel.conf"
```

---

## What This Does

```
System Python (C:\Program Files\Python311\python.exe)
  → Firewall binds to WireGuard interface
  → Traffic routed through 10.2.0.2 (WireGuard tunnel)
  → Appears as: VPN IP (149.40.51.228)

All Other Windows Traffic (browsers, apps, etc.)
  → Uses normal network interface (higher metric)
  → Appears as: Your regular ISP IP

Result: Python gets VPN, everything else direct!
```
