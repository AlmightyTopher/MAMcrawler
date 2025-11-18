# WireGuard Python Tunnel - Quick Start (5 Minutes)

## What This Does

✅ Routes **Python traffic through VPN** (appears as different IP)
✅ Routes **Windows traffic directly** (normal internet)
✅ Works **automatically** - Python scripts use tunnel without modification
✅ Survives **reboots** - tunnel re-activates automatically

## Installation

### 1. Install WireGuard (if not already installed)
```
https://www.wireguard.com/install/
→ Download Windows Installer
→ Run as Administrator
→ Default installation location
```

### 2. Run Setup Script

Open **Administrator PowerShell**:
```powershell
cd C:\Users\dogma\Projects\MAMcrawler
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\setup_wireguard_python_tunnel.ps1
```

**What the script does:**
- Copies config file to WireGuard
- Creates firewall rules for Python
- Configures tunnel

### 3. Activate Tunnel

**Open WireGuard Application** (Start Menu → "WireGuard")
- Find: **TopherTek-Python-Tunnel**
- Click: **"Activate tunnel"** button
- Status: Should show **"Active"** (green text)

### 4. Verify It Works

```powershell
python verify_wireguard.py
```

**Success looks like:**
```
✅ SUCCESS - Two different routes detected!

  Python traffic:  149.40.51.228 (via WireGuard VPN)
  Windows traffic: 203.0.113.45 (direct WAN)
```

If you see **different IPs**, you're done! ✓

---

## Manual Verification

Test without running verify script:

**Python IP (should be VPN):**
```powershell
python -c "import requests; print(requests.get('http://httpbin.org/ip').json()['origin'])"
```

**Windows IP (should be direct):**
```cmd
curl http://httpbin.org/ip
```

If they're **different**, tunnel is working! ✓

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Tunnel doesn't appear in WireGuard | Run setup script again, then restart WireGuard |
| Both IPs are the same | Make sure tunnel is "Active" in WireGuard GUI |
| "Access Denied" errors | Run PowerShell as Administrator |
| Connection timeouts | Check Windows Defender isn't blocking python.exe |

---

## Using the Tunnel

Just run Python scripts normally - they automatically use the tunnel:

```powershell
python scraper_all_audiobooks.py
# Python traffic goes through VPN automatically
```

Or with System Python:
```powershell
"C:\Program Files\Python311\python.exe" run_dual_scraper.py
```

---

## Deactivate Tunnel

**To temporarily disable:**
- Open WireGuard
- Click **"Deactivate tunnel"** button

**To permanently remove:**
```powershell
# Stop service
Stop-Service -Name "wg-quick" -Force

# Remove firewall rules (optional)
Remove-NetFirewallRule -DisplayName "PythonVPN*" -ErrorAction SilentlyContinue

# Delete config
Remove-Item "C:\Program Files\WireGuard\Data\Configurations\TopherTek-Python-Tunnel.conf"
```

---

## Files

| File | Purpose |
|------|---------|
| `TopherTek-Python-Tunnel.conf` | VPN configuration |
| `setup_wireguard_python_tunnel.ps1` | Setup script (run once) |
| `verify_wireguard.py` | Test script |
| `WIREGUARD_SETUP_GUIDE.md` | Full documentation |

---

## That's It!

Your Python tunnel is now ready. Every Python script will automatically use the VPN while Windows uses normal internet.

Questions? See `WIREGUARD_SETUP_GUIDE.md` for detailed troubleshooting.
