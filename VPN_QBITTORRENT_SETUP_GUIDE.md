# VPN & qBittorrent Setup Guide

## Status: ProtonVPN Connected, SOCKS Proxy Not Available

### Diagnostic Results
- **ProtonVPN Status**: ✅ Running (PID: 15468)
- **VPN Adapter**: ✅ Connected (IP: 10.2.0.2)
- **Network IP**: ✅ 159.26.103.83 (through VPN)
- **SOCKS Proxy**: ❌ Not available (required by qBittorrent)

### Problem
qBittorrent cannot communicate with MyAnonamouse (MAM) because it has no way to route traffic through the VPN. ProtonVPN is connected, but the SOCKS5 proxy that qBittorrent needs isn't exposed on port 1080 or other standard ports.

---

## Solution: Configure Port Proxy for qBittorrent

### Method 1: Using the Setup Script (EASIEST)

#### Step 1: Open Command Prompt as Administrator
1. Press **Windows Key + X**
2. Select **"Command Prompt (Admin)"** or **"Windows Terminal (Admin)"**
3. If prompted, click **"Yes"** to allow administrator access

#### Step 2: Navigate to MAMcrawler Directory
```bash
cd C:\Users\dogma\Projects\MAMcrawler
```

#### Step 3: Run the Setup Script
```bash
python setup_vpn_proxy_elevated.py
```

The script will:
- Create a port proxy from 127.0.0.1:1080 to 10.2.0.1:8080
- Verify the configuration was applied correctly
- Display next steps for qBittorrent configuration

### Method 2: Manual Setup (If Script Doesn't Work)

#### Step 1: Open Command Prompt as Administrator
1. Press **Windows Key + X**
2. Select **"Command Prompt (Admin)"** or **"Windows Terminal (Admin)"**

#### Step 2: Create Port Proxy
Copy and paste this command:
```bash
netsh interface portproxy add v4tov4 listenport=1080 listenaddress=127.0.0.1 connectport=8080 connectaddress=10.2.0.1
```

You should see:
```
Ok.
```

#### Step 3: Verify Configuration
```bash
netsh interface portproxy show all
```

Should display:
```
Listen on ipv4:   Connect to ipv4:

Address         Port        Address         Port
-----------     ----------  -----------     ----------
127.0.0.1       1080        10.2.0.1        8080
```

---

## Configure qBittorrent to Use the VPN Proxy

Once the port proxy is set up, configure qBittorrent:

### Step 1: Open qBittorrent
Launch the qBittorrent application

### Step 2: Access Network Settings
1. Go to **Tools** > **Options**
2. Click **Network** in the left sidebar

### Step 3: Configure Proxy Settings
Under **Proxy server** section:

| Setting | Value |
|---------|-------|
| **Proxy Type** | SOCKS5 |
| **IP Address** | 127.0.0.1 |
| **Port** | 1080 |
| **Use proxy for peer connections** | ✓ (CHECK THIS) |
| **Use proxy for tracker connections** | ✓ (CHECK THIS) |

### Step 4: Save Configuration
1. Click **OK** to save settings
2. Restart qBittorrent if it doesn't auto-reconnect

---

## Verify Everything Works

### Test 1: Check Port Proxy Status
```bash
# Open Command Prompt (no admin needed)
netsh interface portproxy show all
```

You should see port 1080 listening.

### Test 2: Check VPN Connectivity
```bash
# In the MAMcrawler directory
python check_vpn_connection.py
```

Should show:
- ✅ ProtonVPN running
- ✅ VPN adapter with IP 10.2.0.2
- ✅ Port 1080 open (after proxy setup)

### Test 3: Test qBittorrent Connection
Add a test torrent to qBittorrent and verify:
- It connects to trackers
- It can see peers
- Network activity shows traffic routing through VPN

---

## Troubleshooting

### Issue: "Port 1080 still not open"
**Solution**: Port proxy is created but may need a Windows restart for some systems.
```bash
# In Command Prompt (Admin)
netsh interface portproxy show all

# If no entry found, try:
netsh interface portproxy add v4tov4 listenport=1080 listenaddress=127.0.0.1 connectport=8080 connectaddress=10.2.0.1

# Restart Windows if still doesn't show
```

### Issue: qBittorrent can't connect to trackers
1. Verify port 1080 is open: `netsh interface portproxy show all`
2. Verify ProtonVPN is still connected: `python check_vpn_connection.py`
3. Try disabling then re-enabling proxy in qBittorrent settings
4. Restart both ProtonVPN and qBittorrent

### Issue: "Connection refused" from qBittorrent
This means:
1. Port proxy isn't created or already deleted
2. ProtonVPN interface (10.2.0.1:8080) is unreachable

**Solution**:
- Reconnect ProtonVPN to a server
- Recreate the port proxy
- Restart qBittorrent

### Issue: Can't run setup as Administrator
If you can't run the script as admin:
1. Right-click on Command Prompt
2. Select "Run as Administrator"
3. Type: `cd C:\Users\dogma\Projects\MAMcrawler`
4. Type: `python setup_vpn_proxy_elevated.py`

---

## Cleanup (If Needed)

To remove the port proxy later:
```bash
# In Command Prompt (Admin)
netsh interface portproxy delete v4tov4 listenport=1080 listenaddress=127.0.0.1
```

---

## Network Architecture

```
qBittorrent
    ↓
127.0.0.1:1080 (SOCKS5 Proxy)
    ↓
Windows Port Proxy (netsh)
    ↓
10.2.0.1:8080 (ProtonVPN Interface)
    ↓
VPN Network
    ↓
MyAnonamouse.net
```

---

## What Each Component Does

| Component | Purpose |
|-----------|---------|
| **ProtonVPN** | Encrypts all traffic through VPN tunnel |
| **Port Proxy** | Routes qBittorrent traffic through VPN interface |
| **qBittorrent** | Uses SOCKS5 proxy to connect to peers/trackers |
| **MAM (MyAnonamouse)** | Receives connections from qBittorrent through VPN |

---

## Files in This Directory

- `vpn_qbittorrent_fix.py` - Full diagnostic tool (run this first)
- `setup_vpn_proxy_elevated.py` - Automated setup script (run with admin)
- `setup_vpn_proxy.ps1` - PowerShell setup script (alternative)
- `setup_vpn_proxy.bat` - Batch file setup (alternative)
- `check_vpn_connection.py` - Verify VPN status
- `VPN_QBITTORRENT_SETUP_GUIDE.md` - This file

---

## Next Steps

1. ✅ Run diagnostic: `python vpn_qbittorrent_fix.py` (DONE)
2. ⚠️ Run setup as admin: `python setup_vpn_proxy_elevated.py`
3. ⚠️ Configure qBittorrent (see instructions above)
4. ⚠️ Test with: `python check_vpn_connection.py`
5. ⚠️ Run Phase 1 downloader: `python PHASE1_WORKING.py`

---

## Summary

**Your VPN is working correctly.** The issue is that qBittorrent needs a SOCKS proxy to access the VPN. The setup script creates a bridge (port proxy) that allows qBittorrent to securely route traffic through ProtonVPN.

Once configured:
- All qBittorrent traffic goes through ProtonVPN
- Your IP shows as VPN IP (currently 159.26.103.83)
- MAM access is anonymous and encrypted

**You're almost there!** Just run the setup script and configure qBittorrent.
