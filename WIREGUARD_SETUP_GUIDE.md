# WireGuard Python-Only Tunnel Setup Guide

## Overview

This guide sets up a **dedicated WireGuard VPN tunnel that routes ONLY Python traffic** through a secure tunnel while leaving the rest of Windows internet traffic on the normal WAN connection.

**Key Benefits:**
- Python scripts use VPN IP (appears as different IP to servers)
- Windows/Browser traffic uses normal direct connection
- Each scraper can use different IPs simultaneously
- No global VPN slowdown (only Python affected)
- Survives reboots with automatic tunnel activation

## Prerequisites

1. **WireGuard Installed**
   - Download from: https://www.wireguard.com/install/
   - Run installer as Administrator
   - Install in default location: `C:\Program Files\WireGuard\`

2. **Python 311 Installed**
   - Should be in: `C:\Program Files\Python311\python.exe`
   - Verify: `"C:\Program Files\Python311\python.exe" --version`

3. **Administrator PowerShell Access**
   - All setup commands require Administrator privileges

4. **WireGuard Config File**
   - Should be in current directory: `TopherTek-Python-Tunnel.conf`
   - Contains pre-configured private/public keys and VPN endpoint

## Quick Start (5 minutes)

### Step 1: Run Setup Script

Open **Administrator PowerShell** and run:

```powershell
cd C:\Users\dogma\Projects\MAMcrawler
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\setup_wireguard_python_tunnel.ps1
```

This script will:
- Copy config file to WireGuard directory
- Start WireGuard service
- Create firewall rules for Python
- Configure network routing

### Step 2: Activate Tunnel in WireGuard GUI

1. Click **Start Menu** → Search for "**WireGuard**"
2. Open **WireGuard Application**
3. Look for tunnel named "**TopherTek-Python-Tunnel**"
4. Click **"Activate tunnel"** button (or Ctrl+U)
5. Status should show "**Active**" in green

### Step 3: Verify Setup Works

Open PowerShell (normal or admin) and run:

```powershell
cd C:\Users\dogma\Projects\MAMcrawler
python verify_wireguard.py
```

**Expected Output:**
```
✅ SUCCESS - Two different routes detected!

  Python traffic:  149.40.51.228 (via WireGuard VPN)
  Windows traffic: 203.0.113.45 (direct WAN)

🎉 Your WireGuard tunnel is working correctly!
```

If you see **different IPs for Python and Windows**, the tunnel is working! ✓

## Manual Setup (If Script Fails)

If `setup_wireguard_python_tunnel.ps1` encounters errors, follow these manual steps:

### Step 1: Copy Config File

```powershell
# Run as Administrator
Copy-Item "C:\Users\dogma\Projects\MAMcrawler\TopherTek-Python-Tunnel.conf" `
    "C:\Program Files\WireGuard\Data\Configurations\TopherTek-Python-Tunnel.conf" -Force
```

Verify it copied:
```powershell
Test-Path "C:\Program Files\WireGuard\Data\Configurations\TopherTek-Python-Tunnel.conf"
```

### Step 2: Create Firewall Rules

**Outbound Rule (Python sends data through VPN):**
```powershell
New-NetFirewallRule -DisplayName "PythonVPN-Outbound-WireGuard" `
    -Direction Outbound `
    -Program "C:\Program Files\Python311\python.exe" `
    -Action Allow `
    -RemotePorts 80,443,8080,8443,13378,51820 `
    -Protocol TCP,UDP `
    -Enabled True
```

**Inbound Rule (Python receives responses):**
```powershell
New-NetFirewallRule -DisplayName "PythonVPN-Inbound-WireGuard" `
    -Direction Inbound `
    -Program "C:\Program Files\Python311\python.exe" `
    -Action Allow `
    -LocalPorts 80,443,8080,8443,13378,51820 `
    -Protocol TCP,UDP `
    -Enabled True
```

### Step 3: Activate Tunnel

1. Open **WireGuard Application**
2. Find **"TopherTek-Python-Tunnel"** in the list
3. Click **"Activate tunnel"**
4. Wait for status to show "**Active**" (green)

### Step 4: Verify Setup

```powershell
python verify_wireguard.py
```

## Troubleshooting

### Issue: Tunnel doesn't appear in WireGuard GUI

**Solution:**
```powershell
# Manually place config in correct location
Copy-Item "TopherTek-Python-Tunnel.conf" `
    "C:\Program Files\WireGuard\Data\Configurations\TopherTek-Python-Tunnel.conf" -Force

# Restart WireGuard
Get-Process WireGuard | Stop-Process -Force
Start-Sleep -Seconds 2
& "C:\Program Files\WireGuard\wireguard.exe"
```

### Issue: "Different IPs" test shows SAME IP for both

**Possible Causes:**
1. Tunnel not activated
2. Firewall rules not applied
3. Python is blocked by Windows Defender

**Solutions:**

Check tunnel status:
```powershell
# Should show Active=True
Get-NetIPConfiguration | Where-Object {$_.InterfaceAlias -like "*WireGuard*"}
```

Check firewall rules:
```powershell
Get-NetFirewallRule -DisplayName "PythonVPN*" | Format-Table -Property DisplayName, Enabled, Action
```

If disabled, enable them:
```powershell
Enable-NetFirewallRule -DisplayName "PythonVPN*"
```

Check Windows Defender:
- Settings → Virus & threat protection → Firewall settings
- Ensure Python is not blocked

### Issue: "Both tests failed" - No internet

**Check:**
```powershell
# Verify internet connection
Test-NetConnection -ComputerName google.com -Port 80

# Check if Python has requests library
python -c "import requests; print('requests OK')"

# Install if missing
pip install requests
```

### Issue: Firewall rules won't create

**Solution - Run PowerShell as Administrator:**
```powershell
# Verify Administrator
([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
# Should print: True
```

## What These Files Do

**TopherTek-Python-Tunnel.conf**
- WireGuard configuration file
- Contains VPN endpoint: `149.40.51.228:51820`
- Interface IP: `10.2.0.2/32`
- Public/Private key pair for VPN authentication

**setup_wireguard_python_tunnel.ps1**
- Automated setup script (run once)
- Copies config to correct location
- Creates firewall rules
- Starts WireGuard service

**verify_wireguard.py**
- Tests that tunnel is working
- Compares Python IP vs Windows IP
- Should show different IPs if working

## Using the Tunnel for Scrapers

Once verified, use System Python for your scraper scripts:

```powershell
# This will use WireGuard tunnel automatically
"C:\Program Files\Python311\python.exe" run_dual_scraper.py
```

Or update shebang in scripts:
```python
#!/C:\Program Files\Python311\python.exe
```

## Network Diagram

```
┌─────────────────────────────────────────────────────────┐
│           Your Computer (Windows 11)                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐         ┌──────────────────┐    │
│  │  Python Scripts  │         │  Windows Apps    │    │
│  │  (Scrapers)      │         │  (Browser, etc)  │    │
│  └────────┬─────────┘         └────────┬─────────┘    │
│           │                            │               │
│           │ (Firewall Routes)          │               │
│           │                            │               │
│  ┌────────▼──────────────┐    ┌───────▼──────────┐   │
│  │   WireGuard Tunnel    │    │   Default WAN    │   │
│  │   (vpn.example.com)   │    │   (ISP Direct)   │   │
│  └────────┬──────────────┘    └───────┬──────────┘   │
│           │                            │               │
└───────────┼────────────────────────────┼───────────────┘
            │                            │
        ┌───▼──────────────┐        ┌────▼──────────────┐
        │   VPN Server     │        │   ISP Gateway     │
        │ 149.40.51.228    │        │ (Your Normal IP)  │
        └──────────────────┘        └───────────────────┘
```

## Security Notes

- Config file contains private key - **Do not share**
- Keep firewall rules enabled at all times
- Tunnel persists across reboots (auto-connects)
- All Python traffic encrypted through VPN
- Windows traffic unaffected

## Reverting Changes

To disable the tunnel:

```powershell
# Deactivate in WireGuard GUI (click Deactivate)
# Or stop service:
Stop-Service -Name "wg-quick" -Force

# Remove firewall rules (optional):
Remove-NetFirewallRule -DisplayName "PythonVPN*" -ErrorAction SilentlyContinue
```

## Next Steps

1. ✅ Run `setup_wireguard_python_tunnel.ps1`
2. ✅ Activate tunnel in WireGuard GUI
3. ✅ Run `verify_wireguard.py` to confirm
4. ✅ Use Python scripts - they'll automatically use VPN
5. Run your dual scrapers with different IPs

---

**Questions?** Check the Troubleshooting section or test manually:
```powershell
python -c "import requests; print(requests.get('http://httpbin.org/ip').json())"
```

This shows which IP Python is using (VPN = 149.40.51.228 range, or WireGuard endpoint).
