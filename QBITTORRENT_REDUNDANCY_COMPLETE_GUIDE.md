# qBittorrent Redundancy - Complete Implementation Guide

**Complete VPN-resilient qBittorrent setup with automatic failover**

**Last Updated:** 2025-11-28
**Status:** Production Ready
**Difficulty:** Intermediate

---

## Quick Start (5 Minutes)

If you just want to get redundancy working quickly:

1. **Install qBittorrent locally** (if not already installed)
2. **Configure Web UI** on port 52095 with same credentials as primary
3. **Add to .env**:
   ```bash
   QBITTORRENT_SECONDARY_URL=http://localhost:52095/
   ```
4. **Test it**:
   ```bash
   python monitor_qbittorrent_health.py
   ```

Done! Your workflow now has automatic failover.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Files Created](#files-created)
3. [Setup Instructions](#setup-instructions)
4. [Configuration Files](#configuration-files)
5. [Testing & Validation](#testing--validation)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)
8. [Implementation Checklist](#implementation-checklist)

---

## Architecture Overview

### The Three-Tier Fallback System

```
User Request (add magnet)
          ↓
┌─────────────────────────────────────────────┐
│   ResilientQBittorrentClient                │
│   (backend/integrations/qbittorrent_        │
│    resilient.py)                            │
└─────────────────────────────────────────────┘
          ↓
    [VPN Health Check]
          ↓
          ├─→ Tier 1: Primary Instance
          │   - Location: 192.168.0.48:52095
          │   - Requires: VPN connection
          │   - Status: Production
          │   - Priority: 1 (try first)
          │
          ├─→ Tier 2: Secondary Instance
          │   - Location: localhost:52095
          │   - Requires: Local qBittorrent running
          │   - Status: Fallback
          │   - Priority: 2 (try if primary fails)
          │
          └─→ Tier 3: Queue File
              - Location: qbittorrent_queue.json
              - Requires: Nothing (always available)
              - Status: Emergency storage
              - Priority: 3 (last resort)
```

### What Happens When...

| Scenario | Behavior | Result |
|----------|----------|--------|
| **VPN connected, primary OK** | Uses primary instance | Ideal state |
| **VPN disconnected, secondary OK** | Uses secondary instance | Failover active |
| **Both instances down** | Saves to queue file | Manual recovery needed |
| **VPN reconnects** | Automatically uses primary again | Primary restored |
| **Queue file exists** | Processes on next run | Automatic recovery |

---

## Files Created

This implementation created the following files in your project:

### 1. Configuration File
**`qbittorrent_secondary_config.ini`**
- Template for configuring local qBittorrent instance
- Pre-configured with recommended settings
- **Location:** Copy to `C:\Users\{YourUsername}\AppData\Roaming\qBittorrent\qBittorrent.ini`

### 2. Queue Processor Script
**`process_qbittorrent_queue.py`**
- Processes magnets from queue file
- Attempts to add them to available instances
- Cleans up queue file after successful processing
- **Usage:** `python process_qbittorrent_queue.py`

### 3. Health Monitor Script
**`monitor_qbittorrent_health.py`** (existing, enhanced)
- Real-time health status of all instances
- VPN connectivity check
- Recommendations for fixing issues
- **Usage:** `python monitor_qbittorrent_health.py`

### 4. Test Suite
**`test_qbittorrent_redundancy.py`**
- Comprehensive test suite (5 tests)
- Validates failover behavior
- Tests queue file creation/processing
- **Usage:** `python test_qbittorrent_redundancy.py`

### 5. Documentation Files
- **`QBITTORRENT_REDUNDANCY_SETUP.md`** - Original setup guide (existing)
- **`QBITTORRENT_REDUNDANCY_COMPLETE_GUIDE.md`** - This comprehensive guide

---

## Setup Instructions

### Step 1: Install qBittorrent Locally

1. **Download**
   - Visit: https://www.qbittorrent.org/download.php
   - Download: Windows installer (latest 4.x version)

2. **Install**
   - Run installer with default settings
   - Install location: `C:\Program Files\qBittorrent\`

3. **DO NOT START YET** (we'll configure first)

### Step 2: Configure Secondary Instance

#### Option A: Use Configuration File (Recommended)

1. **Copy template to qBittorrent directory:**
   ```powershell
   # Close qBittorrent if running
   Stop-Process -Name qbittorrent -Force -ErrorAction SilentlyContinue

   # Copy config template
   $source = "C:\Users\dogma\Projects\MAMcrawler\qbittorrent_secondary_config.ini"
   $dest = "$env:APPDATA\qBittorrent\qBittorrent.ini"

   # Backup existing config
   if (Test-Path $dest) {
       Copy-Item $dest "$dest.backup"
   }

   # Copy template
   Copy-Item $source $dest
   ```

2. **Edit config file:**
   - Open: `%APPDATA%\qBittorrent\qBittorrent.ini`
   - Replace `{YourUsername}` with your actual Windows username
   - Save and close

3. **Create download folders:**
   ```powershell
   New-Item -ItemType Directory -Force -Path "C:\Downloads\Audiobooks"
   New-Item -ItemType Directory -Force -Path "C:\Downloads\Audiobooks\.incomplete"
   New-Item -ItemType Directory -Force -Path "C:\Downloads\Audiobooks\.torrents"
   New-Item -ItemType Directory -Force -Path "C:\Downloads\Audiobooks\.torrents\completed"
   ```

4. **Start qBittorrent and set password:**
   - Launch qBittorrent
   - Go to: Tools → Options → Web UI
   - Verify settings match config
   - **Set password:** Enter `Tesl@ismy#1` (or your preferred password)
   - Click OK

#### Option B: Manual Configuration

If you prefer to configure manually via GUI:

1. **Start qBittorrent**

2. **Enable Web UI:**
   - Tools → Options → Web UI
   - Check: "Enable Web User Interface"
   - IP Address: `127.0.0.1`
   - Port: `52095`
   - Username: `TopherGutbrod`
   - Password: `Tesl@ismy#1`

3. **Configure Downloads:**
   - Tools → Options → Downloads
   - Save path: `C:\Downloads\Audiobooks`
   - Create subfolders: Checked
   - Keep incomplete in: `C:\Downloads\Audiobooks\.incomplete`

4. **Add audiobooks category:**
   - Right-click category panel → Add category
   - Name: `audiobooks`
   - Path: `C:\Downloads\Audiobooks`

### Step 3: Update Environment Variables

Add to your `.env` file:

```bash
# Primary qBittorrent (Remote via VPN)
QBITTORRENT_URL=http://192.168.0.48:52095/
QBITTORRENT_USERNAME=TopherGutbrod
QBITTORRENT_PASSWORD=Tesl@ismy#1

# Secondary qBittorrent (Local Fallback) - ADD THIS LINE
QBITTORRENT_SECONDARY_URL=http://localhost:52095/

# Download path
QBITTORRENT_SAVEPATH=F:/Audiobookshelf/Books
```

### Step 4: Verify Setup

Run the health monitor:

```bash
python monitor_qbittorrent_health.py
```

**Expected Output:**
```
================================================================================
qBittorrent Redundancy Health Check
================================================================================

VPN Status: ✓ Connected
Primary Instance (192.168.0.48:52095): OK
Secondary Instance (localhost:52095): OK
Last Check: 2025-11-28T10:30:00

✓ Full redundancy operational
================================================================================
```

### Step 5: Auto-Start Configuration (Optional)

To ensure secondary instance starts with Windows:

**Using Task Scheduler:**

```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute "C:\Program Files\qBittorrent\qbittorrent.exe"
$trigger = New-ScheduledTaskTrigger -AtLogon
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0

Register-ScheduledTask -TaskName "qBittorrent Secondary Instance" `
                       -Action $action `
                       -Trigger $trigger `
                       -Principal $principal `
                       -Settings $settings
```

---

## Configuration Files

### Environment Variables Reference

```bash
# === REQUIRED ===
QBITTORRENT_URL=http://192.168.0.48:52095/    # Primary instance
QBITTORRENT_USERNAME=TopherGutbrod             # WebUI username
QBITTORRENT_PASSWORD=Tesl@ismy#1               # WebUI password

# === OPTIONAL BUT RECOMMENDED ===
QBITTORRENT_SECONDARY_URL=http://localhost:52095/  # Local fallback
QBITTORRENT_SAVEPATH=F:/Audiobookshelf/Books      # Download folder

# === VPN HEALTH MONITORING ===
VPN_GATEWAY_IP=192.168.0.1                    # VPN gateway to ping
VPN_CHECK_TIMEOUT=5                           # Ping timeout (seconds)
VPN_RECONNECT_WAIT=60                         # Max wait for reconnect

# === QUEUE FILE ===
QBITTORRENT_QUEUE_FILE=qbittorrent_queue.json  # Queue file name
```

### Queue File Format

When both instances are down, magnets are saved to `qbittorrent_queue.json`:

```json
{
  "saved_at": "2025-11-28T10:30:45.123456",
  "reason": "VPN/qBittorrent unavailable",
  "magnets": [
    "magnet:?xt=urn:btih:abc123...&dn=Book+Title",
    "magnet:?xt=urn:btih:def456...&dn=Another+Book"
  ],
  "instructions": "Manually add these to qBittorrent when available, or paste into web UI"
}
```

**Manual Recovery:**
1. Open queue file to see saved magnets
2. Copy magnet links
3. Open http://localhost:52095 (or primary URL)
4. Add → Paste magnets → Download
5. Delete queue file when done

**Automatic Recovery:**
```bash
python process_qbittorrent_queue.py
```

---

## Testing & Validation

### Quick Test

```bash
# Run health check
python monitor_qbittorrent_health.py

# Should show:
# ✓ VPN Connected
# ✓ Primary: OK
# ✓ Secondary: OK
```

### Full Test Suite

Run comprehensive tests:

```bash
python test_qbittorrent_redundancy.py
```

**Tests Included:**
1. **Verify Instances Running** - Both primary and secondary accessible
2. **VPN Failover** - Disconnect VPN, verify secondary takes over
3. **Queue File Creation** - All instances down, verify queue file created
4. **Queue Processing** - Services recover, verify queue is processed
5. **VPN Reconnect** - VPN reconnects, verify primary is used again

**Manual Steps Required:**
- Tests 2-5 require you to disconnect/reconnect VPN manually
- Follow on-screen instructions during test execution

**Skip VPN tests:**
```bash
python test_qbittorrent_redundancy.py --skip-vpn
```

### Test Individual Components

**Test 1 Only (No VPN changes):**
```bash
python test_qbittorrent_redundancy.py --test 1
```

**Test Queue Processing:**
```bash
# Create test queue file
echo '{"saved_at":"2025-11-28T10:30:00","reason":"test","magnets":["magnet:?xt=urn:btih:test&dn=Test"]}' > qbittorrent_queue.json

# Process it
python process_qbittorrent_queue.py
```

---

## Monitoring & Maintenance

### Health Monitoring

**Single Check:**
```bash
python monitor_qbittorrent_health.py
```

**Continuous Monitoring:**
```bash
# Check every 60 seconds
python monitor_qbittorrent_health.py --continuous

# Custom interval (30 seconds)
python monitor_qbittorrent_health.py --interval 30
```

### What to Monitor

1. **Daily:** Check health status once
2. **Weekly:** Run full test suite
3. **Monthly:** Review logs for failover events
4. **After VPN issues:** Run health check

### Log Files

**Workflow Logs:**
- `real_workflow_execution.log` - Main workflow events
- Contains all failover events with timestamps

**Queue Processing Logs:**
- `queue_processing.log` - Queue file processing events
- Created when running `process_qbittorrent_queue.py`

**Searching Logs:**
```powershell
# Find failover events
Select-String -Path "real_workflow_execution.log" -Pattern "failover|VPN_DOWN|secondary"

# Find errors
Select-String -Path "*.log" -Pattern "\[ERROR\]|\[FAIL\]"

# Last 100 lines
Get-Content "real_workflow_execution.log" -Tail 100
```

### Scheduled Monitoring (Optional)

Create Task Scheduler job to run health check daily:

```powershell
$action = New-ScheduledTaskAction -Execute "python.exe" `
    -Argument "C:\Users\dogma\Projects\MAMcrawler\monitor_qbittorrent_health.py"

$trigger = New-ScheduledTaskTrigger -Daily -At 9am

Register-ScheduledTask -TaskName "qBittorrent Health Check" `
                       -Action $action `
                       -Trigger $trigger
```

---

## Troubleshooting

### Common Issues

#### Issue: Secondary instance not responding

**Symptoms:**
```
Secondary Instance (localhost:52095): TIMEOUT
```

**Solutions:**

1. **Check if qBittorrent is running:**
   ```powershell
   Get-Process qbittorrent -ErrorAction SilentlyContinue
   ```

2. **Start qBittorrent:**
   ```powershell
   Start-Process "C:\Program Files\qBittorrent\qbittorrent.exe"
   ```

3. **Verify port 52095 is listening:**
   ```powershell
   netstat -ano | findstr :52095
   ```

4. **Check Web UI is enabled:**
   - Open qBittorrent → Tools → Options → Web UI
   - Verify "Enable Web User Interface" is checked
   - Verify Port is 52095

5. **Test Web UI directly:**
   - Open browser: http://localhost:52095
   - Login with credentials
   - Should see dashboard

#### Issue: Both instances failing

**Symptoms:**
```
⚠️ WARNING: Both instances unavailable!
   → Magnets will be queued to qbittorrent_queue.json
```

**Solutions:**

1. **Start secondary instance:**
   ```powershell
   Start-Process "C:\Program Files\qBittorrent\qbittorrent.exe"
   ```

2. **If VPN down, reconnect VPN**

3. **Process any queued magnets:**
   ```bash
   python process_qbittorrent_queue.py
   ```

4. **Resume workflow:**
   ```bash
   python execute_full_workflow.py
   ```

#### Issue: Queue file not being processed

**Symptoms:**
- `qbittorrent_queue.json` exists
- Running processor does nothing

**Solutions:**

1. **Verify queue file format:**
   ```powershell
   Get-Content qbittorrent_queue.json | ConvertFrom-Json | Format-List
   ```

2. **Check at least one instance is available:**
   ```bash
   python monitor_qbittorrent_health.py
   ```

3. **Run processor with full output:**
   ```bash
   python process_qbittorrent_queue.py
   ```

4. **Manual recovery if automated fails:**
   - Open queue file
   - Copy magnet links
   - Add manually via Web UI

#### Issue: VPN reconnection not detected

**Symptoms:**
- VPN is connected (can ping 192.168.0.1)
- Primary still shows VPN_DOWN

**Solutions:**

1. **Force new health check:**
   ```bash
   python monitor_qbittorrent_health.py
   ```

2. **Verify VPN gateway IP is correct:**
   ```powershell
   # Check gateway
   ipconfig | findstr "Default Gateway"

   # Should match VPN_GATEWAY_IP in .env
   ```

3. **Test ping manually:**
   ```powershell
   ping -n 1 -w 5000 192.168.0.1
   echo $LASTEXITCODE  # Should be 0 if successful
   ```

4. **Restart workflow** to get fresh VPN status

#### Issue: Primary returns HTTP 403

**Symptoms:**
```
Primary Instance: HTTP_403
```

**Solutions:**

1. **Update IP whitelist on primary:**
   - SSH/RDP to 192.168.0.48
   - Open qBittorrent → Options → Web UI
   - Update IP whitelist to include your IP
   - Or set to `0.0.0.0/0` (less secure but allows all)

2. **Check your current IP:**
   ```powershell
   curl ifconfig.me
   ```

3. **Restart remote qBittorrent** after changing whitelist

---

## Implementation Checklist

Use this checklist to track your setup progress:

### Pre-Deployment

- [ ] qBittorrent downloaded from official website
- [ ] Installation completed successfully
- [ ] Download folders created:
  - [ ] `C:\Downloads\Audiobooks`
  - [ ] `C:\Downloads\Audiobooks\.incomplete`
  - [ ] `C:\Downloads\Audiobooks\.torrents`
  - [ ] `C:\Downloads\Audiobooks\.torrents\completed`

### Configuration

- [ ] Web UI enabled on port 52095
- [ ] Username set to `TopherGutbrod`
- [ ] Password set (matches primary)
- [ ] IP address set to `127.0.0.1`
- [ ] Category `audiobooks` created
- [ ] Download paths configured

### Environment Variables

- [ ] `.env` file updated with:
  - [ ] `QBITTORRENT_SECONDARY_URL=http://localhost:52095/`
  - [ ] All other qBittorrent variables present
- [ ] Credentials match between primary and secondary

### Testing

- [ ] Health monitor runs successfully
- [ ] Primary instance shows OK (when VPN connected)
- [ ] Secondary instance shows OK
- [ ] Test 1 passed (both instances running)
- [ ] Test 2 passed (VPN failover works)
- [ ] Test 3 passed (queue file created)
- [ ] Test 4 passed (queue file processed)
- [ ] Test 5 passed (VPN reconnect detected)

### Optional Enhancements

- [ ] Auto-start configured (Task Scheduler)
- [ ] Scheduled health checks configured
- [ ] Log rotation configured
- [ ] Sync script configured (if using different download folders)

### Validation

- [ ] Run workflow with VPN connected → uses primary
- [ ] Disconnect VPN → workflow uses secondary
- [ ] Stop all instances → magnets saved to queue
- [ ] Start instance → queue processed automatically
- [ ] No errors in logs

### Documentation

- [ ] Saved `.env` backup (secure location)
- [ ] Documented any customizations
- [ ] Noted local network specifics
- [ ] Created rollback plan

---

## Quick Reference

### Essential Commands

```bash
# Health check
python monitor_qbittorrent_health.py

# Process queue
python process_qbittorrent_queue.py

# Run tests
python test_qbittorrent_redundancy.py

# Run workflow
python execute_full_workflow.py

# Start secondary instance
Start-Process "C:\Program Files\qBittorrent\qbittorrent.exe"
```

### File Locations

```
Project Root: C:\Users\dogma\Projects\MAMcrawler\

Config Files:
  .env                                    # Environment variables
  qbittorrent_secondary_config.ini        # Secondary config template

Scripts:
  monitor_qbittorrent_health.py           # Health monitoring
  process_qbittorrent_queue.py            # Queue processor
  test_qbittorrent_redundancy.py          # Test suite
  execute_full_workflow.py                # Main workflow

Logs:
  real_workflow_execution.log             # Workflow log
  queue_processing.log                    # Queue processor log

Runtime:
  qbittorrent_queue.json                  # Queue file (created when needed)

Documentation:
  QBITTORRENT_REDUNDANCY_SETUP.md         # Original guide
  QBITTORRENT_REDUNDANCY_COMPLETE_GUIDE.md  # This guide
```

### URLs

```
Primary Instance (VPN):   http://192.168.0.48:52095
Secondary Instance:       http://localhost:52095
VPN Gateway:              192.168.0.1 (for health checks)
```

---

## Summary

You now have a **fully redundant qBittorrent setup** with:

1. **Primary Instance** (Remote via VPN)
   - Production system
   - Higher bandwidth
   - Automatically used when VPN is up

2. **Secondary Instance** (Local)
   - Always available
   - Automatic failover
   - No VPN required

3. **Queue File** (Emergency)
   - Last resort storage
   - Automatic recovery
   - Manual recovery option

4. **VPN Monitoring**
   - Real-time health checks
   - Automatic detection
   - 5-second timeout

5. **Management Tools**
   - Health monitor
   - Queue processor
   - Comprehensive test suite

**Result:** Zero downtime for torrent additions, even during VPN outages!

---

## Next Steps

1. **Test Your Setup**
   ```bash
   python test_qbittorrent_redundancy.py --test 1
   ```

2. **Run Your First Workflow**
   ```bash
   python execute_full_workflow.py
   ```

3. **Monitor Results**
   ```bash
   tail -f real_workflow_execution.log
   ```

4. **Set Up Automatic Monitoring** (Optional)
   - Schedule daily health checks
   - Configure email alerts
   - Set up log rotation

---

## Support

### Getting Help

1. **Check Troubleshooting Section** (above)
2. **Review Logs** for specific error messages
3. **Run Health Check** to identify issues
4. **Consult Original Documentation**:
   - `QBITTORRENT_REDUNDANCY_SETUP.md`
   - `backend/integrations/qbittorrent_resilient.py` (source code)

### Common Questions

**Q: Do I need to sync download folders between instances?**
A: No. Each instance downloads to its own folder. The workflow handles deduplication.

**Q: What happens if I manually add torrents?**
A: That's fine. The resilient client only manages torrents added via the workflow.

**Q: Can I use different ports for primary and secondary?**
A: Yes, but using the same port (52095) keeps configuration simpler.

**Q: What if my VPN uses a different gateway IP?**
A: Set `VPN_GATEWAY_IP` in `.env` to your VPN's gateway address.

**Q: How often should I run health checks?**
A: Daily is fine for manual checks. The workflow checks automatically before each run.

---

**Congratulations!** Your qBittorrent setup is now fully redundant and VPN-resilient.

**Last Updated:** 2025-11-28
**Version:** 1.0
**Author:** MAMcrawler Project
