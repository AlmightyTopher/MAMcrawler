# qBittorrent Redundancy Configuration Guide

## Overview

This guide explains how to set up **redundant qBittorrent instances** to ensure audiobook downloads continue even when the VPN connection to your primary remote instance becomes unavailable.

### What is Redundancy?

Redundancy means having backup systems that automatically take over when the primary system fails. In this workflow:

- **Primary Instance**: Remote qBittorrent (192.168.0.48:52095) via VPN
- **Secondary Instance**: Local qBittorrent (localhost:52095) as fallback
- **Queue File**: JSON file that stores magnets when both instances are unavailable

### Why It Matters

**Without Redundancy:**
- VPN disconnection = workflow stops
- Remote server maintenance = downloads halt
- No ability to recover failed magnet additions

**With Redundancy:**
- Automatic failover to local instance
- Graceful degradation (queue to file if all fails)
- Manual recovery possible from saved queue file
- Zero data loss even during network outages

---

## Architecture Overview

```
Phase 5 (Download)
    ↓
ResilientQBittorrentClient
    ↓
1. Check VPN Health (ping 192.168.0.1)
    ↓
2. Try Primary Instance (192.168.0.48:52095)
    ├─ Success → Download starts
    └─ Failure (VPN down / 403 / timeout)
        ↓
3. Try Secondary Instance (localhost:52095)
    ├─ Success → Download starts (local)
    └─ Failure (not running / error)
        ↓
4. Queue to JSON File (qbittorrent_queue.json)
    └─ Manual recovery when services restore
```

---

## Part 1: Primary Instance Configuration

### Current Setup (Remote via VPN)

**Location**: `C:\Users\dogma\Projects\MAMcrawler\.env`

```bash
# Primary qBittorrent Instance (via VPN)
QBITTORRENT_URL=http://192.168.0.48:52095/
QBITTORRENT_USERNAME=TopherGutbrod
QBITTORRENT_PASSWORD=Tesl@ismy#1
```

### Network Architecture

```
Windows PC (192.168.0.x)
    ↓
ProtonVPN Interface (10.2.0.2)
    ↓
VPN Tunnel (encrypted)
    ↓
Remote Server (192.168.0.48)
    ↓
qBittorrent Web UI (port 52095)
```

### VPN Requirements

1. **ProtonVPN Running**
   - VPN adapter must have IP 10.2.0.2
   - Gateway reachable at 192.168.0.1
   - Port proxy configured (127.0.0.1:1080 → 10.2.0.1:8080)

2. **Network Routing**
   - Verify VPN connectivity: `ping 192.168.0.1`
   - Test remote server: `ping 192.168.0.48`
   - Test qBittorrent API: `curl http://192.168.0.48:52095/api/v2/app/webapiVersion`

3. **Common Issues**
   - **HTTP 403 Forbidden**: IP not whitelisted in qBittorrent Web UI settings
   - **HTTP 404 Not Found**: VPN disconnected or route unavailable
   - **Timeout**: Remote server not responding or firewall blocking

### VPN Health Monitoring

The resilient client automatically monitors VPN connectivity:

```python
# From: backend/integrations/qbittorrent_resilient.py
class VPNHealthChecker:
    def __init__(self, gateway_ip: str = "192.168.0.1", timeout: int = 5):
        # Pings VPN gateway every check
        # Returns: True (connected) or False (down)
```

**Health Check Process:**
1. ICMP ping to VPN gateway (192.168.0.1)
2. 5-second timeout per check
3. Updates `health['vpn_connected']` status
4. Determines if primary instance is accessible

---

## Part 2: Secondary Instance Configuration (Local Fallback)

### Installation Steps (Windows)

#### Step 1: Download qBittorrent

1. Visit: https://www.qbittorrent.org/download.php
2. Download **qBittorrent 4.6.x** (Windows installer)
3. Run installer with default options
4. Install to: `C:\Program Files\qBittorrent\`

#### Step 2: Configure Web UI

1. **Launch qBittorrent**
   - Open from Start Menu

2. **Enable Web UI**
   - Go to: **Tools → Options → Web UI**
   - Check: **"Enable Web User Interface (Remote control)"**
   - Set IP Address: `127.0.0.1` (localhost only)
   - Set Port: `52095` (same as remote)
   - Create credentials:
     - Username: `TopherGutbrod`
     - Password: `Tesl@ismy#1`
   - **IMPORTANT**: Uncheck "Use UPnP / NAT-PMP port forwarding"
   - Click **OK** to save

3. **Configure Downloads Path**
   - Go to: **Tools → Options → Downloads**
   - Default Save Path: `F:\Audiobookshelf\Books`
   - Check: **"Create subfolder for torrents with multiple files"**
   - Check: **"Keep incomplete torrents in:"** `F:\Audiobookshelf\Books\.incomplete`

4. **Set Category for Audiobooks**
   - Right-click in category list (left sidebar)
   - Add New Category: `audiobooks`
   - Save Path: `F:\Audiobookshelf\Books`

5. **Verify Web UI Access**
   - Open browser: http://localhost:52095
   - Login with credentials
   - Should see qBittorrent Web UI dashboard

#### Step 3: Configure Firewall (Optional)

If Windows Firewall blocks local access:

```powershell
# Run in PowerShell as Administrator
New-NetFirewallRule -DisplayName "qBittorrent Web UI Local" `
    -Direction Inbound -Protocol TCP -LocalPort 52095 `
    -Action Allow -Profile Private
```

#### Step 4: Auto-Start Configuration

**Method 1: Task Scheduler (Recommended)**

1. Open Task Scheduler (`taskschd.msc`)
2. Create Basic Task:
   - Name: `qBittorrent Autostart`
   - Trigger: **At log on**
   - Action: **Start a program**
   - Program: `C:\Program Files\qBittorrent\qbittorrent.exe`
   - Arguments: (leave blank)
3. Save task

**Method 2: Startup Folder**

1. Press `Win + R`
2. Type: `shell:startup`
3. Create shortcut to: `C:\Program Files\qBittorrent\qbittorrent.exe`

#### Step 5: Update Environment Variables

Add secondary instance to `.env`:

```bash
# .env (add this line)
QBITTORRENT_SECONDARY_URL=http://localhost:52095/
```

**Full Configuration:**

```bash
# Primary Instance (VPN-based remote)
QBITTORRENT_URL=http://192.168.0.48:52095/
QBITTORRENT_USERNAME=TopherGutbrod
QBITTORRENT_PASSWORD=Tesl@ismy#1

# Secondary Instance (local fallback)
QBITTORRENT_SECONDARY_URL=http://localhost:52095/

# Legacy settings (backward compatibility)
QB_HOST=http://localhost
QB_PORT=52095
QB_USERNAME=TopherGutbrod
QB_PASSWORD=Tesl@ismy#1
```

---

## Part 3: Configuration Synchronization

### Why Synchronization Matters

Both instances should have identical settings to ensure:
- Same download paths (F:\Audiobookshelf\Books)
- Same categories (audiobooks)
- Same speed limits and scheduling
- Consistent seeding behavior

### Settings to Mirror

| Setting | Primary (Remote) | Secondary (Local) | Why Sync? |
|---------|------------------|-------------------|-----------|
| **Web UI Port** | 52095 | 52095 | Code uses same port |
| **Download Path** | F:\Audiobookshelf\Books | F:\Audiobookshelf\Books | Files go to same location |
| **Category: audiobooks** | F:\Audiobookshelf\Books | F:\Audiobookshelf\Books | Workflow sets category |
| **Username/Password** | TopherGutbrod / Tesl@ismy#1 | Same | Same credentials |
| **Seeding Limits** | Ratio: 1.5 / Time: 108h | Same | MAM compliance |

### Manual Synchronization Steps

1. **Export Settings from Primary**
   - SSH/RDP into remote server (192.168.0.48)
   - Locate qBittorrent config: `~/.config/qBittorrent/qBittorrent.conf`
   - Copy relevant sections

2. **Import to Secondary**
   - Local config location: `%APPDATA%\qBittorrent\qBittorrent.ini`
   - Update paths to match local filesystem
   - Restart qBittorrent to apply

3. **Verify Match**
   ```bash
   # Test both instances
   curl http://192.168.0.48:52095/api/v2/app/preferences
   curl http://localhost:52095/api/v2/app/preferences

   # Compare JSON outputs for consistency
   ```

### Automated Synchronization (Future Enhancement)

Create `sync_qbittorrent_settings.py`:

```python
import aiohttp
import asyncio

async def sync_settings():
    # Get settings from primary
    async with aiohttp.ClientSession() as session:
        # Login to primary
        await session.post('http://192.168.0.48:52095/api/v2/auth/login',
                          data={'username': 'TopherGutbrod', 'password': 'Tesl@ismy#1'})

        # Get preferences
        async with session.get('http://192.168.0.48:52095/api/v2/app/preferences') as resp:
            primary_prefs = await resp.json()

        # Login to secondary
        await session.post('http://localhost:52095/api/v2/auth/login',
                          data={'username': 'TopherGutbrod', 'password': 'Tesl@ismy#1'})

        # Update secondary preferences
        await session.post('http://localhost:52095/api/v2/app/setPreferences',
                          json={'prefs': primary_prefs})

if __name__ == '__main__':
    asyncio.run(sync_settings())
```

---

## Part 4: Queue File Processing

### What is the Queue File?

When both primary and secondary instances are unavailable, the resilient client saves magnet links to a JSON file for manual recovery.

**File Location**: `C:\Users\dogma\Projects\MAMcrawler\qbittorrent_queue.json`

### Queue File Format

```json
{
  "saved_at": "2025-11-28T14:30:00",
  "reason": "VPN/qBittorrent unavailable",
  "magnets": [
    "magnet:?xt=urn:btih:abc123&dn=Book+Title+1",
    "magnet:?xt=urn:btih:def456&dn=Book+Title+2"
  ],
  "instructions": "Manually add these to qBittorrent when available, or paste into web UI"
}
```

### Manual Recovery Process

**When VPN/qBittorrent Restores:**

1. **Check for Queue File**
   ```bash
   # In project directory
   dir qbittorrent_queue.json
   ```

2. **View Queued Magnets**
   ```bash
   type qbittorrent_queue.json
   ```

3. **Add via Web UI (Manual)**
   - Open: http://192.168.0.48:52095 (or http://localhost:52095)
   - Click **Add Torrent** (plus icon)
   - Paste magnets (one per line)
   - Set Category: `audiobooks`
   - Set Save Path: `F:\Audiobookshelf\Books`
   - Click **Add Torrents**

4. **Add via Script (Automatic)**
   ```python
   # Run this in project directory
   python -c "import asyncio; from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient; asyncio.run(ResilientQBittorrentClient('http://192.168.0.48:52095', 'TopherGutbrod', 'Tesl@ismy#1').process_queue_file())"
   ```

### Automated Queue Processing

The resilient client can automatically process queued magnets:

```python
# From: backend/integrations/qbittorrent_resilient.py
async def process_queue_file(self) -> Tuple[List[str], List[str]]:
    """Process queued magnets that were previously saved"""
    if not self.queue_file.exists():
        return [], []

    queue_data = json.loads(self.queue_file.read_text())
    magnets = queue_data.get('magnets', [])

    # Try to add them with fallback support
    successful, failed, queued = await self.add_torrents_with_fallback(magnets)

    # Clean up file if all processed
    if not queued:
        self.queue_file.unlink()

    return successful, failed
```

**Usage in Workflow:**

Add to beginning of Phase 5 in `execute_full_workflow.py`:

```python
# Phase 5: Add to qBittorrent
self.log("PHASE 5: QBITTORRENT DOWNLOAD", "PHASE")

# FIRST: Process any queued magnets from previous failures
queued_successful, queued_failed = await qb_client.process_queue_file()
if queued_successful:
    self.log(f"Recovered {len(queued_successful)} queued magnets from previous run", "OK")

# THEN: Add new magnets
added = await self.add_to_qbittorrent(magnet_links, max_downloads=10)
```

---

## Part 5: Monitoring Health Status

### Real-Time Health Checks

The resilient client provides detailed health status:

```python
# Example usage
from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient

async with ResilientQBittorrentClient(
    primary_url="http://192.168.0.48:52095",
    secondary_url="http://localhost:52095",
    username="TopherGutbrod",
    password="Tesl@ismy#1"
) as client:
    health = await client.perform_health_check()
    print(health)
```

**Sample Health Output:**

```python
{
    'primary': 'OK',                    # or 'VPN_DOWN', 'TIMEOUT', 'HTTP_403'
    'secondary': 'OK',                  # or 'NOT_CONFIGURED', 'TIMEOUT'
    'vpn_connected': True,              # VPN gateway ping result
    'last_check': '2025-11-28T14:30:00',
    'active_instance': 'primary'        # or 'secondary', 'queued'
}
```

### Health Status Meanings

| Status | Meaning | Action Required |
|--------|---------|----------------|
| `OK` | Instance responding normally | None |
| `VPN_DOWN` | VPN gateway unreachable | Reconnect VPN |
| `HTTP_403` | IP not whitelisted | Update Web UI settings |
| `HTTP_404` | Endpoint not found | Check URL/VPN routing |
| `TIMEOUT` | Request exceeded 5 seconds | Check network/firewall |
| `NOT_CONFIGURED` | Secondary URL not set | Add to .env |

### Monitoring Script

Create `monitor_qbittorrent_health.py`:

```python
#!/usr/bin/env python3
"""Monitor qBittorrent redundancy health"""

import asyncio
import os
from dotenv import load_dotenv
from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient

load_dotenv()

async def monitor():
    primary_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
    secondary_url = os.getenv('QBITTORRENT_SECONDARY_URL', 'http://localhost:52095/')
    username = os.getenv('QBITTORRENT_USERNAME')
    password = os.getenv('QBITTORRENT_PASSWORD')

    async with ResilientQBittorrentClient(
        primary_url=primary_url,
        secondary_url=secondary_url,
        username=username,
        password=password
    ) as client:
        print("=" * 60)
        print("qBittorrent Redundancy Health Check")
        print("=" * 60)

        health = await client.perform_health_check()

        print(f"\nVPN Status: {'✓ Connected' if health['vpn_connected'] else '✗ Disconnected'}")
        print(f"Primary Instance (192.168.0.48:52095): {health['primary']}")
        print(f"Secondary Instance (localhost:52095): {health['secondary']}")
        print(f"Last Check: {health['last_check']}")
        print()

        # Recommendations
        if health['primary'] != 'OK' and health['secondary'] != 'OK':
            print("⚠️  WARNING: Both instances unavailable!")
            print("   → Magnets will be queued to qbittorrent_queue.json")
        elif health['primary'] != 'OK':
            print("⚠️  Primary instance unavailable, using secondary")
            print("   → Check VPN connection and remote server")
        elif health['secondary'] != 'OK':
            print("ℹ️  Secondary instance unavailable (primary OK)")
            print("   → Start local qBittorrent for full redundancy")
        else:
            print("✓ Full redundancy operational")

        print("=" * 60)

if __name__ == '__main__':
    asyncio.run(monitor())
```

**Usage:**

```bash
# Run health check
python monitor_qbittorrent_health.py

# Output:
# ============================================================
# qBittorrent Redundancy Health Check
# ============================================================
#
# VPN Status: ✓ Connected
# Primary Instance (192.168.0.48:52095): OK
# Secondary Instance (localhost:52095): OK
# Last Check: 2025-11-28T14:30:00
#
# ✓ Full redundancy operational
# ============================================================
```

---

## Part 6: Troubleshooting

### Issue 1: Primary Instance Returns HTTP 403

**Symptom:**
```
Primary qBittorrent returning 403 (Forbidden)
Health: {'primary': 'HTTP_403', 'secondary': 'OK', 'vpn_connected': True}
```

**Cause**: IP whitelist in qBittorrent Web UI doesn't include your current IP.

**Solution:**

1. **SSH/RDP into remote server** (192.168.0.48)

2. **Open qBittorrent** (or edit config directly)

3. **Go to Options → Web UI**

4. **Update IP Whitelist:**
   - Add your current VPN IP (check with: `curl ifconfig.me`)
   - Or set to: `0.0.0.0/0` (allow all - less secure)

5. **Restart qBittorrent** on remote server

6. **Re-test:**
   ```bash
   python monitor_qbittorrent_health.py
   ```

### Issue 2: VPN Disconnected (HTTP 404)

**Symptom:**
```
Primary instance returning 404 (VPN issue?)
Health: {'primary': 'VPN_DOWN', 'vpn_connected': False}
```

**Cause**: ProtonVPN disconnected or VPN adapter down.

**Solution:**

1. **Check VPN Status:**
   ```bash
   # Windows
   ipconfig | findstr "10.2.0"

   # Should show: IPv4 Address: 10.2.0.2
   ```

2. **Reconnect VPN:**
   - Open ProtonVPN app
   - Connect to preferred server
   - Wait for connection to establish

3. **Verify Port Proxy:**
   ```bash
   netsh interface portproxy show all

   # Should show: 127.0.0.1:1080 → 10.2.0.1:8080
   ```

4. **Re-test Connectivity:**
   ```bash
   ping 192.168.0.1          # VPN gateway
   ping 192.168.0.48         # Remote server
   curl http://192.168.0.48:52095/api/v2/app/webapiVersion
   ```

### Issue 3: Secondary Instance Not Starting

**Symptom:**
```
Health: {'primary': 'OK', 'secondary': 'TIMEOUT'}
```

**Cause**: Local qBittorrent not running or port conflict.

**Solution:**

1. **Check if Running:**
   ```powershell
   Get-Process qbittorrent -ErrorAction SilentlyContinue
   ```

2. **Check Port 52095:**
   ```powershell
   netstat -ano | findstr :52095
   ```

3. **Start qBittorrent:**
   - Launch from Start Menu
   - Or run: `"C:\Program Files\qBittorrent\qbittorrent.exe"`

4. **Verify Web UI:**
   - Open: http://localhost:52095
   - Login with credentials
   - Should show dashboard

### Issue 4: Both Instances Down

**Symptom:**
```
⚠️  WARNING: Both instances unavailable!
   → Magnets will be queued to qbittorrent_queue.json
```

**Cause**: VPN down AND local qBittorrent not running.

**Solution:**

1. **Start Secondary Instance:**
   ```powershell
   Start-Process "C:\Program Files\qBittorrent\qbittorrent.exe"
   ```

2. **Wait 10 seconds for startup**

3. **Process Queue File:**
   ```bash
   python -c "import asyncio; from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient; asyncio.run(ResilientQBittorrentClient('http://localhost:52095', 'TopherGutbrod', 'Tesl@ismy#1').process_queue_file())"
   ```

4. **Resume Workflow:**
   ```bash
   python execute_full_workflow.py
   ```

### Issue 5: Magnets Not Added After VPN Restore

**Symptom:**
- VPN reconnected
- Primary instance now `OK`
- Queue file still exists with magnets

**Cause**: Automatic queue processing not integrated into workflow.

**Solution:**

**Manual Processing:**
```bash
# Check queue file
type qbittorrent_queue.json

# Process manually via Web UI
# → Copy magnets from JSON
# → Paste into http://192.168.0.48:52095
```

**Automated Processing:**

Add to start of Phase 5 in `execute_full_workflow.py`:

```python
async def add_to_qbittorrent(self, magnet_links: List[str], max_downloads: int = 10) -> List[str]:
    """Add books to qBittorrent with resilient fallback"""

    # Import resilient client
    from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient

    self.log(f"Adding {min(len(magnet_links), max_downloads)} books to qBittorrent...", "DOWNLOAD")

    try:
        # Use resilient client
        async with ResilientQBittorrentClient(
            primary_url=self.qb_url,
            secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL', 'http://localhost:52095/'),
            username=self.qb_user,
            password=self.qb_pass
        ) as client:
            # First: Process any queued magnets
            queued_success, queued_fail = await client.process_queue_file()
            if queued_success:
                self.log(f"Recovered {len(queued_success)} queued magnets", "OK")

            # Second: Add new magnets with fallback
            successful, failed, queued = await client.add_torrents_with_fallback(
                magnet_links[:max_downloads]
            )

            self.log(f"Added: {len(successful)}, Failed: {len(failed)}, Queued: {len(queued)}", "OK")

            return successful

    except Exception as e:
        self.log(f"Resilient qBittorrent error: {e}", "FAIL")
        return []
```

---

## Part 7: Testing Procedures

### Test 1: Verify Redundancy Failover

**Objective**: Confirm automatic failover from primary to secondary.

**Steps:**

1. **Start with Both Running**
   ```bash
   python monitor_qbittorrent_health.py
   # Should show: Primary: OK, Secondary: OK
   ```

2. **Disconnect VPN**
   - Open ProtonVPN app
   - Click "Disconnect"

3. **Check Health Again**
   ```bash
   python monitor_qbittorrent_health.py
   # Should show: Primary: VPN_DOWN, Secondary: OK
   ```

4. **Run Test Download**
   ```python
   # test_resilient_download.py
   import asyncio
   from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient

   async def test():
       async with ResilientQBittorrentClient(
           primary_url="http://192.168.0.48:52095",
           secondary_url="http://localhost:52095",
           username="TopherGutbrod",
           password="Tesl@ismy#1"
       ) as client:
           # This should use secondary since primary is down
           test_magnet = ["magnet:?xt=urn:btih:test&dn=Test"]
           success, fail, queued = await client.add_torrents_with_fallback(test_magnet)

           print(f"Success: {len(success)}")
           print(f"Failed: {len(fail)}")
           print(f"Queued: {len(queued)}")
           print(f"Active instance: {client.health['active_instance']}")

   asyncio.run(test())
   ```

5. **Expected Result:**
   ```
   Success: 1
   Failed: 0
   Queued: 0
   Active instance: secondary
   ```

6. **Reconnect VPN**
   - Connect ProtonVPN
   - Re-run health check (should show Primary: OK)

### Test 2: Queue File Creation

**Objective**: Verify magnets are saved when both instances fail.

**Steps:**

1. **Stop Both Instances**
   ```powershell
   # Disconnect VPN
   # Stop local qBittorrent
   Stop-Process -Name qbittorrent -Force
   ```

2. **Run Test Download**
   ```python
   # test_queue_creation.py
   import asyncio
   from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient

   async def test():
       async with ResilientQBittorrentClient(
           primary_url="http://192.168.0.48:52095",
           secondary_url="http://localhost:52095",
           username="TopherGutbrod",
           password="Tesl@ismy#1"
       ) as client:
           test_magnets = [
               "magnet:?xt=urn:btih:test1&dn=Test+Book+1",
               "magnet:?xt=urn:btih:test2&dn=Test+Book+2"
           ]
           success, fail, queued = await client.add_torrents_with_fallback(test_magnets)

           print(f"Queued: {len(queued)}")

   asyncio.run(test())
   ```

3. **Verify Queue File Created**
   ```bash
   type qbittorrent_queue.json
   ```

4. **Expected Output:**
   ```json
   {
     "saved_at": "2025-11-28T15:00:00",
     "reason": "VPN/qBittorrent unavailable",
     "magnets": [
       "magnet:?xt=urn:btih:test1&dn=Test+Book+1",
       "magnet:?xt=urn:btih:test2&dn=Test+Book+2"
     ],
     "instructions": "Manually add these to qBittorrent when available..."
   }
   ```

### Test 3: Queue File Processing

**Objective**: Verify queued magnets are recovered when services restore.

**Steps:**

1. **Ensure Queue File Exists** (from Test 2)

2. **Restore Services**
   ```powershell
   # Start local qBittorrent
   Start-Process "C:\Program Files\qBittorrent\qbittorrent.exe"

   # Wait 10 seconds
   Start-Sleep -Seconds 10
   ```

3. **Process Queue**
   ```python
   # test_queue_processing.py
   import asyncio
   from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient

   async def test():
       async with ResilientQBittorrentClient(
           primary_url="http://192.168.0.48:52095",
           secondary_url="http://localhost:52095",
           username="TopherGutbrod",
           password="Tesl@ismy#1"
       ) as client:
           success, fail = await client.process_queue_file()

           print(f"Recovered: {len(success)}")
           print(f"Failed: {len(fail)}")

   asyncio.run(test())
   ```

4. **Expected Result:**
   ```
   Recovered: 2
   Failed: 0
   ```

5. **Verify File Deleted:**
   ```bash
   dir qbittorrent_queue.json
   # Should show: File Not Found
   ```

### Test 4: Full Workflow Integration

**Objective**: Test redundancy during actual workflow execution.

**Steps:**

1. **Prepare Test Environment**
   - Ensure secondary qBittorrent running
   - VPN can be connected or disconnected (to test both paths)

2. **Run Full Workflow**
   ```bash
   python execute_full_workflow.py
   ```

3. **Monitor Phase 5 Logs**
   ```
   [2025-11-28 15:00:00] [PHASE] PHASE 5: QBITTORRENT DOWNLOAD
   [2025-11-28 15:00:01] [INFO ] Performing qBittorrent health check...
   [2025-11-28 15:00:02] [INFO ] Health check results: {'primary': 'OK', 'secondary': 'OK', 'vpn_connected': True}
   [2025-11-28 15:00:03] [INFO ] Attempting primary instance for magnet...
   [2025-11-28 15:00:04] [OK   ] Successfully added via primary
   ```

4. **Simulate VPN Failure Mid-Workflow**
   - During Phase 5, disconnect VPN
   - Workflow should automatically failover to secondary

5. **Expected Logs:**
   ```
   [2025-11-28 15:01:00] [WARN ] Primary failed: VPN_DOWN
   [2025-11-28 15:01:01] [INFO ] Attempting secondary instance for magnet...
   [2025-11-28 15:01:02] [OK   ] Successfully added via secondary
   ```

---

## Part 8: Network Configuration

### Port Requirements

| Service | Port | Protocol | Direction | Purpose |
|---------|------|----------|-----------|---------|
| **qBittorrent Web UI (Remote)** | 52095 | TCP | Inbound | API access |
| **qBittorrent Web UI (Local)** | 52095 | TCP | Loopback | Local API |
| **SOCKS Proxy** | 1080 | TCP | Loopback | VPN routing |
| **ProtonVPN Interface** | 8080 | TCP | Outbound | VPN tunnel |

### Firewall Rules (Windows)

**Allow qBittorrent Web UI (Local):**

```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "qBittorrent Web UI Local" `
    -Direction Inbound -Protocol TCP -LocalPort 52095 `
    -Action Allow -Profile Private -Program "C:\Program Files\qBittorrent\qbittorrent.exe"
```

**Allow SOCKS Proxy:**

```powershell
New-NetFirewallRule -DisplayName "SOCKS Proxy for VPN" `
    -Direction Inbound -Protocol TCP -LocalPort 1080 `
    -Action Allow -Profile Private
```

**Verify Rules:**

```powershell
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*qBittorrent*"}
```

### Port Proxy Configuration

**Setup VPN Port Proxy:**

```bash
# Run as Administrator
netsh interface portproxy add v4tov4 listenport=1080 listenaddress=127.0.0.1 connectport=8080 connectaddress=10.2.0.1
```

**Verify Configuration:**

```bash
netsh interface portproxy show all

# Expected Output:
# Listen on ipv4:   Connect to ipv4:
# Address         Port        Address         Port
# -----------     ----------  -----------     ----------
# 127.0.0.1       1080        10.2.0.1        8080
```

**Remove Proxy (if needed):**

```bash
netsh interface portproxy delete v4tov4 listenport=1080 listenaddress=127.0.0.1
```

### Testing Network Connectivity

**Test Primary Instance (via VPN):**

```bash
# Ping VPN gateway
ping 192.168.0.1

# Ping remote server
ping 192.168.0.48

# Test qBittorrent API
curl -v http://192.168.0.48:52095/api/v2/app/webapiVersion
```

**Test Secondary Instance (local):**

```bash
# Test localhost binding
netstat -ano | findstr :52095

# Test API
curl -v http://localhost:52095/api/v2/app/webapiVersion
```

**Test Port Proxy:**

```bash
# Check if listening
netstat -ano | findstr :1080

# Test connection through proxy
curl --socks5 127.0.0.1:1080 http://example.com
```

---

## Part 9: Example Commands Reference

### Health Monitoring

```bash
# Quick health check
python monitor_qbittorrent_health.py

# Continuous monitoring (every 30 seconds)
while ($true) { python monitor_qbittorrent_health.py; Start-Sleep -Seconds 30 }
```

### Queue Management

```bash
# View queue file
type qbittorrent_queue.json

# Process queue manually
python -c "import asyncio; from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient; asyncio.run(ResilientQBittorrentClient('http://localhost:52095', 'TopherGutbrod', 'Tesl@ismy#1').process_queue_file())"

# Delete queue file (if manually added via Web UI)
del qbittorrent_queue.json
```

### Service Management

```bash
# Start local qBittorrent
Start-Process "C:\Program Files\qBittorrent\qbittorrent.exe"

# Stop local qBittorrent
Stop-Process -Name qbittorrent -Force

# Check if running
Get-Process qbittorrent -ErrorAction SilentlyContinue
```

### VPN Management

```bash
# Check VPN status
ipconfig | findstr "10.2.0"

# Verify port proxy
netsh interface portproxy show all

# Reconnect VPN (manual via ProtonVPN app)
```

### Testing Downloads

```python
# test_add_magnet.py
import asyncio
from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient

async def test():
    async with ResilientQBittorrentClient(
        primary_url="http://192.168.0.48:52095",
        secondary_url="http://localhost:52095",
        username="TopherGutbrod",
        password="Tesl@ismy#1"
    ) as client:
        # Check health first
        health = await client.perform_health_check()
        print(f"Health: {health}")

        # Add test magnet
        test_magnets = ["magnet:?xt=urn:btih:test&dn=Test"]
        success, fail, queued = await client.add_torrents_with_fallback(test_magnets)

        print(f"Success: {len(success)}, Failed: {len(fail)}, Queued: {len(queued)}")

asyncio.run(test())
```

---

## Summary

### Quick Setup Checklist

- [ ] **Primary Instance (Remote via VPN)**
  - [ ] VPN connected (10.2.0.2)
  - [ ] Port proxy configured (1080 → 8080)
  - [ ] Remote qBittorrent accessible (192.168.0.48:52095)
  - [ ] IP whitelisted in Web UI settings

- [ ] **Secondary Instance (Local)**
  - [ ] qBittorrent installed
  - [ ] Web UI enabled on localhost:52095
  - [ ] Same credentials as primary
  - [ ] Same download path (F:\Audiobookshelf\Books)
  - [ ] Category 'audiobooks' created
  - [ ] Auto-start configured

- [ ] **Environment Configuration**
  - [ ] `QBITTORRENT_URL` set to primary
  - [ ] `QBITTORRENT_SECONDARY_URL` set to secondary
  - [ ] Credentials in .env file

- [ ] **Testing**
  - [ ] Health check passes
  - [ ] Primary instance accessible
  - [ ] Secondary instance accessible
  - [ ] Failover works (disconnect VPN test)
  - [ ] Queue file creation works
  - [ ] Queue file processing works

### Key Takeaways

1. **Redundancy = Zero Downtime**
   - VPN fails → Secondary takes over
   - Both fail → Queue to file
   - Services restore → Auto-recover

2. **Three-Tier Fallback**
   - Tier 1: Primary (remote via VPN)
   - Tier 2: Secondary (local)
   - Tier 3: Queue file (manual recovery)

3. **Automatic Health Monitoring**
   - VPN connectivity checked every request
   - Endpoints validated before use
   - Detailed status reporting

4. **Zero Configuration Required**
   - Just set environment variables
   - Resilient client handles everything
   - No code changes to workflow

### Next Steps

1. **Install Secondary Instance**
   - Follow Part 2 instructions
   - Configure Web UI on localhost:52095

2. **Update Environment Variables**
   - Add `QBITTORRENT_SECONDARY_URL` to .env

3. **Test Redundancy**
   - Run `monitor_qbittorrent_health.py`
   - Simulate VPN failure
   - Verify failover works

4. **Integrate into Workflow**
   - Modify Phase 5 in `execute_full_workflow.py`
   - Use `ResilientQBittorrentClient` instead of direct API calls
   - Add queue processing at start of Phase 5

---

## Files Reference

| File | Purpose |
|------|---------|
| `backend/integrations/qbittorrent_resilient.py` | Resilient client implementation |
| `execute_full_workflow.py` | Main workflow (Phase 5 uses qBittorrent) |
| `.env` | Environment configuration |
| `qbittorrent_queue.json` | Queued magnets (created automatically) |
| `monitor_qbittorrent_health.py` | Health monitoring script (create this) |

---

**Questions or Issues?** Check the troubleshooting section (Part 6) or create an issue in the project repository.
