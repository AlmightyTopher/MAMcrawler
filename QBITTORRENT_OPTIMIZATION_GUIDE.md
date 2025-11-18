# qBittorrent Optimization Guide for MyAnonamouse

**Comprehensive implementation guide based on MAM forum insights and best practices**

Last Updated: 2025-11-05

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Essential Configuration](#essential-configuration)
3. [Advanced Optimization](#advanced-optimization)
4. [VPN Integration](#vpn-integration)
5. [Docker Setup](#docker-setup)
6. [Troubleshooting](#troubleshooting)
7. [Automation Scripts](#automation-scripts)

---

## Quick Start

### Prerequisites

- qBittorrent 4.3.9+ (or 5.0.1+ recommended)
- Port forwarding enabled on router/firewall
- Static local IP (recommended)
- VPN with port forwarding (optional but recommended)

### Validation Tool

Run the automated validator to check your configuration:

```bash
python validate_qbittorrent_config.py
```

This will check all critical settings against MAM best practices.

---

## Essential Configuration

### 1. Port Configuration ⚡ CRITICAL

**Why it matters**: Proper port configuration is essential for connectivity with other peers.

**Recommended Settings**:
- Port range: **45000-60000** (optimal for MAM)
- Legacy range: 40000-60000 (still acceptable)
- Avoid blocked ports: 1-1024, 1214, 4662, 6346-6347, 6881-6889

**How to configure**:

1. Open qBittorrent → Tools → Options → Connection
2. Set "Port used for incoming connections" to a random number between 45000-60000
3. Enable "Use UPnP / NAT-PMP port forwarding from my router"
4. Forward this port in your router settings
5. Verify at [canyouseeme.org](http://www.canyouseeme.org/)

**Command-line verification**:
```bash
curl http://canyouseeme.org:80/?port=YOUR_PORT
```

### 2. Anonymous Mode ⚡ CRITICAL

**Why it matters**: Anonymous mode causes MAM to reject your client.

**Required Setting**: **DISABLED**

**How to configure**:
1. Open qBittorrent → Tools → Options → BitTorrent
2. Find "Enable anonymous mode"
3. **ENSURE IT IS UNCHECKED**
4. Save and restart qBittorrent

**Validation**:
```bash
# Should return False
curl -u admin:password http://localhost:8080/api/v2/app/preferences | grep anonymous_mode
```

### 3. Upload Speed Limits

**Why it matters**: Prevents network congestion while maximizing seeding performance.

**Recommended Settings**:
- Cap upload to **80% of maximum upload speed**
- Minimum 5 KB/s per upload slot
- Excellent seeders: 20+ KB/s per slot

**How to configure**:

1. Test your upload speed at [speedtest.net](http://www.speedtest.net/)
2. Calculate 80% of your max upload speed
3. Open qBittorrent → Tools → Options → Speed
4. Set "Upload" to 80% of max speed (in KB/s)
5. Use [Torrent Calculator](http://infinite-source.de/az/az-calc.html) for precise settings

**Example**:
- Max upload: 50 Mbps = 6250 KB/s
- Set limit to: 5000 KB/s (80%)

### 4. Connection Settings

**Why it matters**: Affects how many peers you can connect to simultaneously.

**Recommended Settings**:
- Global maximum connections: **1000+** (for large collections)
- Maximum connections per torrent: 100
- Maximum upload slots per torrent: 15

**How to configure**:
1. Open qBittorrent → Tools → Options → Connection
2. Set "Global maximum number of connections" to 1000 (adjust based on system)
3. Set "Maximum number of connections per torrent" to 100
4. Open BitTorrent tab
5. Set "Maximum number of upload slots per torrent" to 15

---

## Advanced Optimization

### Port Forwarding Strategies

#### Static Port Forwarding (Simple Setup)

**Best for**: Home networks without VPN

1. Choose a port in range 45000-60000
2. Set static local IP on your computer
3. Forward port in router to your static IP
4. Configure qBittorrent to use this port
5. Verify at canyouseeme.org

#### Dynamic Port Forwarding (VPN Setup)

**Best for**: VPN users (ProtonVPN, PIA, Windscribe)

**Challenges**:
- VPN may change ports on reconnect
- Requires automation to update qBittorrent

**Solution**: Use port update script (see Automation Scripts section)

### Connection Optimization

#### Global Max Connections

**Formula**: `Number of torrents × 50`

**Examples**:
- 10 torrents = 500 connections
- 50 torrents = 2500 connections
- 100+ torrents = 5000+ connections

**System Requirements**:
- RAM: 2 GB minimum, 4 GB+ recommended for 100+ torrents
- CPU: Dual-core minimum, quad-core+ for heavy loads

#### Per-Torrent Limits

**Seeding only**:
- Max connections: 100
- Max upload slots: 15

**Downloading**:
- Max connections: 200
- Max upload slots: 15

### Torrent Queuing Strategy

#### Unlimited Seeding (Recommended for MAM)

**Best for**: Good bandwidth, always-on systems

**Configuration**:
1. Tools → Options → BitTorrent
2. **Uncheck** "Torrent Queueing"
3. All torrents will seed simultaneously

**Benefits**:
- Maximum bonus points (earning from all torrents)
- No H&R risk from paused torrents
- Better availability for rare torrents

#### Smart Queueing (Limited Bandwidth)

**Best for**: Limited bandwidth, part-time seeders

**Configuration**:
1. Tools → Options → BitTorrent
2. **Check** "Torrent Queueing"
3. Set "Maximum active torrents" based on bandwidth
4. Set "Maximum active uploads" to same value

**Example Settings** (10 Mbps upload):
- Maximum active torrents: 10
- Maximum active uploads: 10
- Maximum active downloads: 3

### Disk I/O Optimization

#### SSD Configuration

**Settings**:
- Disk cache: 1024-2048 MB
- Async I/O threads: 8-16
- File pool size: 5000

**Configuration**:
1. Tools → Options → Advanced → Disk cache
2. Set "Disk cache" to 1024 MB (increase for more torrents)
3. Set "Disk cache expiry interval" to 600 seconds
4. Enable "Coalesce reads & writes"

#### HDD Configuration

**Settings**:
- Disk cache: 512-1024 MB
- Async I/O threads: 4-8
- File pool size: 1000

**Important**: Lower cache for HDDs to avoid excessive seeking

### Batch Operations Best Practices

**Adding Multiple Torrents**:

1. Add all torrents in **PAUSED** state
2. Wait for all to be added
3. Select all → Right-click → Force Recheck
4. Wait for all to complete checking
5. Select all → Right-click → Resume

**Why this matters**:
- Prevents overwhelming the client
- Ensures proper file verification
- Avoids corrupted data on MAM

---

## VPN Integration

### Recommended VPN Providers

**Port Forwarding Support**:
- ✓ ProtonVPN (recommended)
- ✓ Private Internet Access (PIA)
- ✓ Windscribe
- ✗ NordVPN (no port forwarding)
- ✗ ExpressVPN (no port forwarding)

### ASN-Locked Sessions (Highly Recommended)

**What is it**: MAM session locked to your VPN provider's network (ASN) instead of specific IP.

**Why use it**:
- VPN IPs change frequently
- ASN stays consistent within provider
- Prevents "Unrecognized Host/PassKey" errors

**How to enable**:

1. Log into MyAnonamouse
2. Go to Security → Sessions
3. Create new session with current VPN IP
4. Once created, edit session
5. Change from "IP-locked" to "ASN-locked"

**Verification**:
- Check that your MAM torrents connect properly
- Monitor for passkey errors in qBittorrent
- Should see no errors after switching to ASN

### ProtonVPN Configuration

#### OpenVPN Setup

**Username format**: `USERNAME+pmp`
- Example: `myuser+pmp`

**Why**: The `+pmp` enables port forwarding

**Configuration**:
```
client
proto udp
remote PROTON_SERVER_IP 1194
auth-user-pass /path/to/credentials.txt
```

**Credentials file** (`credentials.txt`):
```
myuser+pmp
mypassword
```

#### WireGuard Setup

**Better performance**, but requires Gluetun for port forwarding automation.

See Docker Setup section for full configuration.

### Dynamic Port Update Script

**Problem**: VPN changes forwarded port on reconnect.

**Solution**: Automatically update qBittorrent port via API.

**Script** (`update_qb_port.sh`):
```bash
#!/bin/bash

# Get forwarded port from VPN
FORWARDED_PORT=$(cat /path/to/forwarded_port.txt)

# qBittorrent details
QB_HOST="localhost"
QB_PORT="8080"
QB_USER="admin"
QB_PASS="password"

# Update port
curl -i -X POST \
  -d "json={\"listen_port\": ${FORWARDED_PORT}}" \
  "http://${QB_HOST}:${QB_PORT}/api/v2/app/setPreferences" \
  --user "${QB_USER}:${QB_PASS}"

echo "Updated qBittorrent port to ${FORWARDED_PORT}"
```

**Make executable**:
```bash
chmod +x update_qb_port.sh
```

**Automate with cron** (runs every 5 minutes):
```bash
*/5 * * * * /path/to/update_qb_port.sh >> /var/log/qb_port_update.log 2>&1
```

---

## Docker Setup

### Basic Docker Compose (Gluetun + qBittorrent)

**File**: `docker-compose.yml`

```yaml
version: "3.8"

services:
  gluetun:
    image: qmcgaw/gluetun:latest
    container_name: gluetun
    cap_add:
      - NET_ADMIN
    environment:
      - VPN_SERVICE_PROVIDER=custom
      - VPN_TYPE=wireguard
      - VPN_PORT_FORWARDING=on
      - VPN_PORT_FORWARDING_PROVIDER=protonvpn
      - FIREWALL_OUTBOUND_SUBNETS=192.168.1.0/24  # Adjust to your network
      - TZ=America/New_York
    volumes:
      - ./gluetun:/gluetun
    ports:
      - "8080:8080"  # qBittorrent Web UI
      - "6881:6881"  # qBittorrent listening port (will be overridden by VPN)
      - "6881:6881/udp"
    restart: unless-stopped

  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent:latest
    container_name: qbittorrent
    network_mode: "service:gluetun"  # Route through VPN
    depends_on:
      - gluetun
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
      - WEBUI_PORT=8080
    volumes:
      - ./qbittorrent/config:/config
      - ./downloads:/downloads
    restart: unless-stopped
```

**Start services**:
```bash
docker-compose up -d
```

**Check logs**:
```bash
docker-compose logs -f gluetun
docker-compose logs -f qbittorrent
```

### Advanced Setup with Seedbox API

**Automatically updates MAM with changing VPN IPs**

**Add to `docker-compose.yml`**:

```yaml
  mam-seedbox-api:
    image: myanonamouse/seedboxapi:latest
    container_name: mam-seedbox
    network_mode: "service:gluetun"
    depends_on:
      - gluetun
    environment:
      - mam_id=YOUR_MAM_SESSION_ID
      - DEBUG=1
      - TZ=America/New_York
    volumes:
      - ./mam_cookies:/config
    restart: unless-stopped
```

**Get your MAM session ID**:
1. Log into MAM
2. Open browser developer tools (F12)
3. Go to Application → Cookies
4. Find `mam_id` cookie value
5. Use this value in docker-compose.yml

### Port Forwarding Automation (Gluetun)

**Add to Gluetun environment**:

```yaml
environment:
  - VPN_PORT_FORWARDING_UP_COMMAND=/scripts/update_port.sh
```

**Create script** (`gluetun/scripts/update_port.sh`):

```bash
#!/bin/sh

# Read forwarded port from Gluetun
FORWARDED_PORT=$(cat /tmp/gluetun/forwarded_port)

# Update qBittorrent
curl -X POST \
  -d "json={\"listen_port\": ${FORWARDED_PORT}}" \
  "http://localhost:8080/api/v2/app/setPreferences" \
  --user "admin:adminpass"

echo "$(date): Updated qBittorrent port to ${FORWARDED_PORT}" >> /config/port_updates.log
```

**Make executable**:
```bash
chmod +x gluetun/scripts/update_port.sh
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. "Unrecognized Host / PassKey Error"

**Symptom**: MAM torrents show authentication errors in qBittorrent

**Causes**:
- VPN IP changed
- Session locked to old IP
- Browser session expired

**Solutions**:
1. Switch to ASN-locked sessions (see VPN Integration section)
2. Use dynamic seedbox API container
3. Update MAM session with new IP manually

**Manual IP update**:
```bash
# Update MAM cookies
curl -c /path/to/mam_cookies \
     -b /path/to/mam_cookies \
     https://t.myanonamouse.net/json/dynamicSeedbox.php
```

#### 2. Port Not Open / Not Connectable

**Symptom**: qBittorrent shows no connectivity, MAM shows red/yellow icon

**Check 1 - Port forwarding**:
```bash
curl http://canyouseeme.org:80/?port=YOUR_PORT
```

**Check 2 - Windows Firewall** (Windows 11):

**Problem**: Lazy loading blocks ports

**Solution**:
1. Open Windows Defender Firewall with Advanced Security
2. Disable "Lazy Loading" in advanced settings
3. Create inbound rule:
   - Protocol: TCP/UDP
   - Ports: 45000-60000
   - Action: Allow
4. Create outbound rule (same settings)
5. Ensure qBittorrent is allowed on both Private and Public networks

**PowerShell commands**:
```powershell
# Allow qBittorrent through firewall
New-NetFirewallRule -DisplayName "qBittorrent Inbound" -Direction Inbound -Protocol TCP -LocalPort 45000-60000 -Action Allow
New-NetFirewallRule -DisplayName "qBittorrent Inbound UDP" -Direction Inbound -Protocol UDP -LocalPort 45000-60000 -Action Allow
New-NetFirewallRule -DisplayName "qBittorrent Outbound" -Direction Outbound -Protocol TCP -LocalPort 45000-60000 -Action Allow
New-NetFirewallRule -DisplayName "qBittorrent Outbound UDP" -Direction Outbound -Protocol UDP -LocalPort 45000-60000 -Action Allow
```

**Check 3 - VPN port forwarding**:
- Verify VPN provider supports it
- Check VPN client settings
- For OpenVPN: Ensure `+pmp` in username
- For WireGuard: Use Gluetun automation

#### 3. Hyper-V Networking Conflicts

**Symptom**: Intermittent connectivity issues, random disconnects

**Causes**: Windows Hyper-V and Docker networking conflicts

**Solutions**:

**Option 1** - Disable Hyper-V (if not needed):
```powershell
# Run as Administrator
Disable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All
```

**Option 2** - Use alternative virtualization:
- VirtualBox
- VMware Workstation
- WSL2 without Hyper-V backend

**Option 3** - Reconfigure Hyper-V networking:
1. Open Hyper-V Manager
2. Virtual Switch Manager
3. Remove conflicting switches
4. Recreate with proper settings

#### 4. Connection Timeouts / Slow Tracker Updates

**Symptom**: Torrents stuck on "Checking tracker", slow peer discovery

**Causes**:
- Too many active torrents
- VPN instability
- ISP throttling

**Solutions**:

**Reduce active torrents**:
1. Enable torrent queueing
2. Set max active torrents to 10-20
3. Monitor performance

**Check VPN stability**:
```bash
# Docker logs
docker-compose logs -f gluetun | grep -i health

# Look for healthcheck failures
```

**Restart on VPN reconnect**:
```bash
# Add to cron (every hour)
0 * * * * docker restart qbittorrent
```

#### 5. Docker Container Won't Start

**Symptom**: `docker-compose up` fails, container exits immediately

**Common causes**:

**Check 1 - Port conflicts**:
```bash
# Find what's using port 8080
netstat -ano | findstr :8080
```

**Check 2 - Permission issues**:
```bash
# Fix volume permissions
sudo chmod -R a+rwx ./qbittorrent/config
sudo chmod -R a+rwx ./downloads
```

**Check 3 - Network conflicts**:
```bash
# Remove old networks
docker network prune

# Recreate containers
docker-compose down
docker-compose up -d
```

**Check logs**:
```bash
docker-compose logs qbittorrent
docker-compose logs gluetun
```

---

## Automation Scripts

### Script 1: qBittorrent Health Monitor

**Purpose**: Monitor qBittorrent health and restart if needed

**File**: `monitor_qbittorrent.sh`

```bash
#!/bin/bash

QB_HOST="localhost"
QB_PORT="8080"
QB_USER="admin"
QB_PASS="password"

# Check if qBittorrent is responding
if ! curl -s --user "${QB_USER}:${QB_PASS}" \
     "http://${QB_HOST}:${QB_PORT}/api/v2/app/version" > /dev/null; then

    echo "$(date): qBittorrent not responding, restarting..."

    # Docker restart
    docker restart qbittorrent

    # Or system service restart
    # systemctl restart qbittorrent

    sleep 30

    # Check again
    if curl -s --user "${QB_USER}:${QB_PASS}" \
       "http://${QB_HOST}:${QB_PORT}/api/v2/app/version" > /dev/null; then
        echo "$(date): qBittorrent restarted successfully"
    else
        echo "$(date): qBittorrent restart FAILED - manual intervention required"
        # Send notification (email, webhook, etc.)
    fi
fi
```

**Cron job** (check every 15 minutes):
```bash
*/15 * * * * /path/to/monitor_qbittorrent.sh >> /var/log/qb_monitor.log 2>&1
```

### Script 2: MAM Session Validator

**Purpose**: Verify MAM connectivity and update cookies

**File**: `validate_mam_session.sh`

```bash
#!/bin/bash

MAM_COOKIES="/path/to/mam_cookies.txt"
QB_HOST="localhost"
QB_PORT="8080"
QB_USER="admin"
QB_PASS="password"

# Update MAM cookies
curl -c "${MAM_COOKIES}" \
     -b "${MAM_COOKIES}" \
     https://t.myanonamouse.net/json/dynamicSeedbox.php

# Check for passkey errors in qBittorrent
ERRORS=$(curl -s --user "${QB_USER}:${QB_PASS}" \
         "http://${QB_HOST}:${QB_PORT}/api/v2/torrents/info" | \
         grep -c "Unrecognized")

if [ "$ERRORS" -gt 0 ]; then
    echo "$(date): Found ${ERRORS} passkey errors - MAM session may need update"
    echo "$(date): Visit MAM Security → Sessions to verify IP/ASN lock"
fi
```

**Cron job** (check daily):
```bash
0 2 * * * /path/to/validate_mam_session.sh >> /var/log/mam_session.log 2>&1
```

### Script 3: Batch Torrent Force Recheck

**Purpose**: Force recheck all torrents in a category

**File**: `force_recheck_category.py`

```python
#!/usr/bin/env python3
"""Force recheck all torrents in a specific category."""

import requests
import sys

QB_HOST = "localhost"
QB_PORT = "8080"
QB_USER = "admin"
QB_PASS = "password"
CATEGORY = sys.argv[1] if len(sys.argv) > 1 else "audiobooks-auto"

# Login
session = requests.Session()
session.post(
    f"http://{QB_HOST}:{QB_PORT}/api/v2/auth/login",
    data={"username": QB_USER, "password": QB_PASS}
)

# Get torrents in category
torrents = session.get(
    f"http://{QB_HOST}:{QB_PORT}/api/v2/torrents/info",
    params={"category": CATEGORY}
).json()

print(f"Found {len(torrents)} torrents in category '{CATEGORY}'")

# Pause all
for torrent in torrents:
    session.post(
        f"http://{QB_HOST}:{QB_PORT}/api/v2/torrents/pause",
        data={"hashes": torrent['hash']}
    )

print("Paused all torrents")

# Force recheck all
for torrent in torrents:
    session.post(
        f"http://{QB_HOST}:{QB_PORT}/api/v2/torrents/recheck",
        data={"hashes": torrent['hash']}
    )

print("Force recheck started for all torrents")
print("Wait for rechecking to complete, then resume manually")
```

**Usage**:
```bash
python force_recheck_category.py audiobooks-auto
```

---

## Quick Reference

### Essential Ports

| Port Range | Purpose |
|------------|---------|
| 45000-60000 | Recommended qBittorrent listening ports |
| 40000-60000 | Legacy acceptable range |
| 8080 | Default Web UI port |
| 6881 | Default listening port (change this!) |

### Connection Limits by Collection Size

| Torrents | Global Max Connections | Per-Torrent Connections |
|----------|----------------------|-------------------------|
| 1-10 | 500 | 100 |
| 11-50 | 1000 | 100 |
| 51-100 | 2500 | 100 |
| 100+ | 5000+ | 50-100 |

### Upload Speed Guidelines

| Connection Type | Max Upload | Recommended Cap (80%) |
|----------------|-----------|---------------------|
| DSL (1 Mbps) | 125 KB/s | 100 KB/s |
| Cable (10 Mbps) | 1250 KB/s | 1000 KB/s |
| Cable (50 Mbps) | 6250 KB/s | 5000 KB/s |
| Fiber (100 Mbps) | 12500 KB/s | 10000 KB/s |
| Fiber (1 Gbps) | 125000 KB/s | 100000 KB/s |

### VPN Providers Comparison

| Provider | Port Forwarding | ASN-Locked Compatible | Notes |
|----------|----------------|----------------------|-------|
| ProtonVPN | ✓ Yes | ✓ Yes | Recommended, add `+pmp` to username |
| PIA | ✓ Yes | ✓ Yes | Reliable port forwarding |
| Windscribe | ✓ Yes | ✓ Yes | Good alternative |
| NordVPN | ✗ No | N/A | Not recommended for torrenting |
| ExpressVPN | ✗ No | N/A | Not recommended for torrenting |

### Critical Settings Checklist

- [ ] Port: 45000-60000 range ✓
- [ ] Anonymous mode: DISABLED ✓
- [ ] Upload limit: 80% of max ✓
- [ ] Global max connections: 1000+ ✓
- [ ] UPnP/NAT-PMP: ENABLED ✓
- [ ] Torrent queuing: Based on bandwidth ✓
- [ ] Port forwarding: Verified ✓
- [ ] MAM session: ASN-locked (if VPN) ✓

---

## Additional Resources

### Official MAM Guides

- [qBittorrent Settings Guide](https://www.myanonamouse.net/guides/?gid=31646)
- [Being a Good Seeder](https://www.myanonamouse.net/guides/?gid=38940)
- [Port Forwarding Guide](https://www.myanonamouse.net/guides/?gid=75694)
- [Static IP Setup](https://www.myanonamouse.net/guides/?gid=77872)

### External Tools

- [Port Checker](http://www.canyouseeme.org/)
- [Speed Test](http://www.speedtest.net/)
- [Torrent Calculator](http://infinite-source.de/az/az-calc.html)
- [Port Forward Router Guides](http://www.portforward.com/)

### Project Scripts

- `validate_qbittorrent_config.py` - Automated configuration validator
- `validate_mam_compliance.py` - Overall MAM compliance checker
- `audiobook_auto_batch.py` - Automated audiobook downloader with qBittorrent integration

---

## Support

If you encounter issues not covered in this guide:

1. Check MAM forums for similar issues
2. Review qBittorrent logs in Web UI
3. Verify VPN connectivity and port forwarding
4. Run validation script: `python validate_qbittorrent_config.py`
5. Check Docker logs: `docker-compose logs -f`

**Remember**: Never share your MAM passkey, session ID, or credentials publicly.

---

**Last Updated**: 2025-11-05
**Based on**: MAM forum insights, official guides, and community best practices
