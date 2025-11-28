# Secondary qBittorrent Instance - Documentation Index

**Complete documentation for setting up and operating a resilient secondary qBittorrent instance for VPN failover support.**

---

## Overview

This documentation set provides everything needed to deploy a **zero-downtime qBittorrent failover system** that automatically switches between primary (VPN-connected) and secondary (local) instances.

### What This Solves

- **VPN disconnections** causing download failures
- **Single point of failure** in qBittorrent setup
- **Manual intervention** required when primary instance unavailable
- **Lost downloads** when VPN drops

### What You Get

- **Automatic failover** from primary to secondary instance
- **Zero downtime** - downloads continue even if VPN drops
- **Queue file fallback** - magnets saved if both instances fail
- **Health monitoring** - real-time status of both instances
- **Easy deployment** - automated PowerShell setup script

---

## Quick Start

### 30-Second Setup (Automated)

```powershell
# 1. Open PowerShell as Administrator
# 2. Navigate to project
cd C:\Users\dogma\Projects\MAMcrawler

# 3. Run setup script
powershell -ExecutionPolicy Bypass -File setup_secondary_qbittorrent.ps1

# 4. Follow prompts (press Y to confirm)
# 5. Set password on first WebUI login (http://localhost:52095)
# 6. Done!
```

### 5-Minute Verification

```powershell
# Check health status
python monitor_qbittorrent_health.py

# Expected output:
# ✓ VPN Connected
# ✓ Primary Instance OK
# ✓ Secondary Instance OK
```

---

## Documentation Files

### 1. **SECONDARY_QBITTORRENT_SETUP.md** (Main Guide)

   **Size:** ~39 KB | **Read Time:** 20-30 minutes

   **Comprehensive setup guide covering:**
   - Overview and architecture
   - Step-by-step installation (manual)
   - Configuration details
   - Verification procedures
   - Troubleshooting (15+ common issues)
   - Integration with workflow
   - Monitoring and maintenance

   **When to use:** First-time setup, detailed reference, troubleshooting

   **Sections:**
   - [Overview](#) - What secondary instance is and why you need it
   - [Installation & Configuration](#) - 6 detailed setup steps
   - [Verification & Testing](#) - 6 verification procedures
   - [Configuration Details](#) - Deep dive into how it works
   - [Common Issues & Solutions](#) - 15+ troubleshooting scenarios
   - [Running Both Instances Together](#) - Operational scenarios
   - [Integration with Workflow](#) - How execute_full_workflow.py uses it
   - [Monitoring](#) - Health checks and queue management
   - [Production Checklist](#) - Final verification before deployment

---

### 2. **setup_secondary_qbittorrent.ps1** (Automated Setup Script)

   **Size:** ~17 KB | **Execution Time:** 2-3 minutes

   **PowerShell script that automates:**
   - Directory structure creation
   - Configuration file setup
   - Batch file generation
   - Desktop shortcut creation
   - Firewall rule configuration
   - .env file updates
   - Permission testing
   - Complete verification

   **When to use:** Automated deployment, quick reinstall, mass deployment

   **Requirements:**
   - Windows PowerShell 5.1+
   - Administrator privileges
   - qBittorrent already installed

   **Usage:**
   ```powershell
   # Right-click → Run with PowerShell
   # OR
   powershell -ExecutionPolicy Bypass -File setup_secondary_qbittorrent.ps1
   ```

---

### 3. **SECONDARY_DEPLOYMENT_CHECKLIST.md** (Deployment Checklist)

   **Size:** ~18 KB | **Read Time:** 15-20 minutes

   **Comprehensive checklist covering:**
   - Pre-deployment verification (15 items)
   - Deployment options (automated + manual)
   - Post-deployment verification (30+ items)
   - Troubleshooting checklists
   - Rollback procedures
   - Production sign-off

   **When to use:** Production deployments, team deployments, audit requirements

   **Phases:**
   1. Pre-Deployment (system requirements, prerequisites)
   2. Deployment (automated OR manual steps)
   3. Post-Deployment Verification (7 phases)
   4. Troubleshooting (quick fixes)
   5. Rollback Procedure (if deployment fails)
   6. Production Sign-Off (formal approval)
   7. Post-Deployment Monitoring (ongoing)

---

### 4. **SECONDARY_QUICK_REFERENCE.md** (Quick Reference)

   **Size:** ~9 KB | **Read Time:** 5 minutes

   **Quick access guide for:**
   - Common commands (start, stop, check health)
   - Key file locations
   - Configuration summary table
   - Troubleshooting quick fixes
   - One-liners for common tasks
   - Testing scenarios
   - Daily operations
   - Emergency procedures

   **When to use:** Daily operations, quick troubleshooting, command reference

   **Perfect for:**
   - Bookmarking for quick access
   - Printing as cheat sheet
   - Copy-paste commands
   - Quick problem resolution

---

## Document Selection Guide

**Choose your document based on your goal:**

| Goal | Document | Time Required |
|------|----------|---------------|
| **Quick automated setup** | setup_secondary_qbittorrent.ps1 | 3 minutes |
| **First-time manual setup** | SECONDARY_QBITTORRENT_SETUP.md | 30 minutes |
| **Production deployment** | SECONDARY_DEPLOYMENT_CHECKLIST.md | 45 minutes |
| **Daily operations** | SECONDARY_QUICK_REFERENCE.md | 5 minutes |
| **Troubleshooting** | SECONDARY_QBITTORRENT_SETUP.md (Common Issues) | 10-15 minutes |
| **Understanding how it works** | SECONDARY_QBITTORRENT_SETUP.md (Configuration Details) | 15 minutes |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    execute_full_workflow.py                     │
│                  (Phase 5: qBittorrent Integration)             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  ResilientQBittorrentClient  │
           │   (VPN Health + Failover)    │
           └──────────────┬───────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Perform Health Check │
              └───────────┬───────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
   ┌────────┐      ┌───────────┐    ┌──────────┐
   │  VPN   │      │  PRIMARY  │    │SECONDARY │
   │ Check  │      │ Instance  │    │ Instance │
   └────┬───┘      └─────┬─────┘    └────┬─────┘
        │                │                │
        │                │                │
   Connected?         OK (200)?        OK (200)?
        │                │                │
        ▼                ▼                ▼
   ┌─────────────────────────────────────────┐
   │         Failover Decision Tree          │
   ├─────────────────────────────────────────┤
   │ 1. VPN UP + Primary OK → Use Primary    │
   │ 2. VPN DOWN / Primary FAIL → Secondary  │
   │ 3. Both FAIL → Queue to JSON            │
   └─────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
   ┌────────┐      ┌───────────┐    ┌──────────┐
   │Primary │      │Secondary  │    │ Queue    │
   │192.168 │      │localhost  │    │ File     │
   │.0.48   │      │:52095     │    │ JSON     │
   │:52095  │      │           │    │          │
   └────────┘      └───────────┘    └──────────┘
        │                │                │
        ▼                ▼                ▼
   F:\Audio...     C:\qb_sec...    qbittorrent_
                    downloads\      queue.json
```

---

## Key Concepts

### Port Configuration

| Instance | IP Address | WebUI Port | BitTorrent Ports |
|----------|-----------|------------|------------------|
| **Primary** | 192.168.0.48 | 52095 | 6881-6900 |
| **Secondary** | 127.0.0.1 (localhost) | 52095 | 6881-6920 |

**Why same WebUI port?**
- Different IP addresses prevent conflict
- Consistent port number simplifies configuration
- Failover logic only changes IP, not port

### Directory Isolation

| Instance | Profile Location | Downloads Location |
|----------|-----------------|-------------------|
| **Primary** | Remote server AppData | F:\Audiobookshelf\Books\ |
| **Secondary** | C:\qbittorrent_secondary\profile\ | C:\qbittorrent_secondary\downloads\ |

**Why separate?**
- Prevents database lock conflicts
- Avoids configuration overwrites
- Isolates download files
- Allows independent management

### Failover Logic

**Decision Flow:**

1. **Health Check** (before adding magnets)
   - Check VPN connectivity (ping 192.168.0.1)
   - Check primary instance (HTTP GET /api/v2/app/webapiVersion)
   - Check secondary instance (HTTP GET /api/v2/app/webapiVersion)

2. **Instance Selection**
   - If VPN UP + Primary OK → Use primary
   - If VPN DOWN or Primary FAIL → Try secondary
   - If both FAIL → Queue to JSON file

3. **Retry Logic**
   - 3 retries per instance
   - Exponential backoff (2s, 4s, 8s)
   - Falls back to next instance after retries exhausted

4. **Queue Recovery**
   - Queued magnets saved with timestamp
   - Auto-processed when services restore
   - Manual processing available via CLI

---

## Environment Variables

**Required in `.env` file:**

```ini
# Primary instance (via VPN)
QBITTORRENT_URL=http://192.168.0.48:52095/

# Secondary instance (local fallback)
QBITTORRENT_SECONDARY_URL=http://localhost:52095/

# Authentication (same for both)
QBITTORRENT_USERNAME=TopherGutbrod
QBITTORRENT_PASSWORD=your_password_here
```

**Optional:**

```ini
# Queue file location (default: project root)
QBITTORRENT_QUEUE_FILE=qbittorrent_queue.json

# VPN gateway for health checks (default: 192.168.0.1)
VPN_GATEWAY=192.168.0.1
```

---

## Common Operations

### Start Secondary Instance

```powershell
# Desktop shortcut (easiest)
# Double-click "qBittorrent Secondary" on Desktop

# OR batch file
C:\qbittorrent_secondary\start_secondary.bat

# OR command line
set APPDATA=C:\qbittorrent_secondary\profile
"C:\Program Files (x86)\qBittorrent\qbittorrent.exe" --webui-port=52095 --profile=C:\qbittorrent_secondary\profile
```

### Check Health Status

```powershell
cd C:\Users\dogma\Projects\MAMcrawler
python monitor_qbittorrent_health.py
```

**Sample output:**

```
======================================================================
qBittorrent Redundancy Health Check
======================================================================

VPN Status:        ✓ Connected
Primary Instance:  ✓ OK (http://192.168.0.48:52095/)
Secondary Instance: ✓ OK (http://localhost:52095/)
Last Check:        2025-11-28T14:30:00

✓ EXCELLENT: Full redundancy operational
   → Both instances healthy and ready
   → Automatic failover available if VPN drops
======================================================================
```

### Stop Secondary Instance

```powershell
# Method 1: Close console window

# Method 2: PowerShell one-liner
Get-NetTCPConnection -LocalPort 52095 -LocalAddress 127.0.0.1 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

### Process Queue File

```powershell
cd C:\Users\dogma\Projects\MAMcrawler

python -c "import asyncio; from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient; import os; from dotenv import load_dotenv; load_dotenv(); asyncio.run(ResilientQBittorrentClient(os.getenv('QBITTORRENT_URL'), os.getenv('QBITTORRENT_USERNAME'), os.getenv('QBITTORRENT_PASSWORD'), os.getenv('QBITTORRENT_SECONDARY_URL')).process_queue_file())"
```

---

## Testing Scenarios

### Test Failover (VPN Disconnect)

```powershell
# 1. Check initial state (both healthy)
python monitor_qbittorrent_health.py

# 2. Disconnect VPN (ProtonVPN → Disconnect)

# 3. Check failover state
python monitor_qbittorrent_health.py
# Expected: Primary VPN_DOWN, Secondary OK

# 4. Run workflow (optional)
python execute_full_workflow.py
# Expected: Uses secondary, downloads succeed

# 5. Reconnect VPN

# 6. Verify restoration
python monitor_qbittorrent_health.py
# Expected: Both OK, primary restored
```

### Test Manual Magnet Add

```powershell
# 1. Start secondary
C:\qbittorrent_secondary\start_secondary.bat

# 2. Open WebUI
Start-Process http://localhost:52095

# 3. Login with credentials (TopherGutbrod / your-password)

# 4. Add test magnet (Ubuntu ISO)
# magnet:?xt=urn:btih:e83a2b5c1c5b6b3a8c4c9b1c5b5c6b3a8c4c9b1c&dn=ubuntu-20.04.1-desktop-amd64.iso

# 5. Verify download starts
Get-ChildItem C:\qbittorrent_secondary\downloads

# 6. Clean up (delete torrent via WebUI)
```

---

## Troubleshooting

### Quick Diagnostic

```powershell
# 1. Check if secondary is running
netstat -ano | findstr 52095

# 2. Check health
python monitor_qbittorrent_health.py

# 3. Check queue file
Get-Item C:\Users\dogma\Projects\MAMcrawler\qbittorrent_queue.json

# 4. Check logs (if exists)
Get-ChildItem C:\qbittorrent_secondary\profile\qBittorrent\logs
```

### Common Issues

| Symptom | Likely Cause | Quick Fix |
|---------|-------------|-----------|
| **"Port already in use"** | Another process on 52095 | Kill process: `Stop-Process -Id (Get-NetTCPConnection -LocalPort 52095 -LocalAddress 127.0.0.1).OwningProcess -Force` |
| **"Invalid credentials"** | Password mismatch | Check `.env` file, reset via WebUI |
| **Health check TIMEOUT** | Secondary not running | Start secondary instance |
| **Both instances failing** | VPN + local both down | Reconnect VPN, start secondary |
| **Downloads wrong location** | Using wrong instance | Verify which instance added torrent |

**For detailed troubleshooting, see:**
- SECONDARY_QBITTORRENT_SETUP.md (Common Issues section)
- SECONDARY_DEPLOYMENT_CHECKLIST.md (Troubleshooting Checklist)

---

## Maintenance Schedule

### Daily
- *(Optional)* Run health check before workflow

### Weekly
- [ ] Run `python monitor_qbittorrent_health.py`
- [ ] Verify both instances accessible
- [ ] Check download folder disk space

### Monthly
- [ ] Review logs for errors
- [ ] Test failover (disconnect VPN temporarily)
- [ ] Verify .env credentials still valid

### Quarterly
- [ ] Update qBittorrent (if new version available)
- [ ] Review download folder size
- [ ] Clean up old/completed torrents

---

## Related Documentation

### Phase 5 Integration
- **PHASE_5_VPN_RESILIENT_INTEGRATION.md** - Complete Phase 5 documentation
- **VPN_RESILIENT_QUICK_START.md** - Quick start for VPN resilience

### Redundancy Setup
- **QBITTORRENT_REDUNDANCY_SETUP.md** - High-level redundancy overview
- **INTEGRATION_CHANGES_SUMMARY.md** - Summary of all integration changes

### Testing
- **test_qbittorrent_redundancy.py** - Automated test suite
- **end_to_end_test_suite.py** - Complete end-to-end tests
- **monitor_qbittorrent_health.py** - Health monitoring script

---

## Support Resources

### Documentation
- **Main Setup Guide:** SECONDARY_QBITTORRENT_SETUP.md
- **Deployment Checklist:** SECONDARY_DEPLOYMENT_CHECKLIST.md
- **Quick Reference:** SECONDARY_QUICK_REFERENCE.md
- **This Index:** README_SECONDARY_QBITTORRENT.md

### Scripts
- **Automated Setup:** setup_secondary_qbittorrent.ps1
- **Health Monitor:** monitor_qbittorrent_health.py
- **Testing Suite:** test_qbittorrent_redundancy.py

### Configuration
- **Template Config:** qbittorrent_secondary_config.ini
- **Environment File:** .env (must configure QBITTORRENT_SECONDARY_URL)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-28 | Initial documentation set |

---

## Success Criteria

**Your secondary qBittorrent instance is successfully deployed when:**

- [ ] Automated setup script completed without errors
- [ ] Both instances accessible (primary + secondary)
- [ ] Health check shows both instances OK
- [ ] Failover tested (disconnect VPN, workflow still works)
- [ ] Queue file tested (both instances down, magnets queued)
- [ ] Environment variables configured in .env
- [ ] Desktop shortcut works (one-click start)
- [ ] Documentation reviewed and bookmarked

---

## Quick Start Summary

**Complete deployment in under 5 minutes:**

```powershell
# 1. Run automated setup
cd C:\Users\dogma\Projects\MAMcrawler
powershell -ExecutionPolicy Bypass -File setup_secondary_qbittorrent.ps1

# 2. Start secondary (follow script prompt or manual)
C:\qbittorrent_secondary\start_secondary.bat

# 3. Set password (first launch only)
# Browser: http://localhost:52095
# Login: admin / adminadmin
# Change to: TopherGutbrod / your-password

# 4. Verify health
python monitor_qbittorrent_health.py

# 5. Done! ✓
```

---

**For questions or issues, refer to the troubleshooting sections in:**
- SECONDARY_QBITTORRENT_SETUP.md (Common Issues)
- SECONDARY_DEPLOYMENT_CHECKLIST.md (Troubleshooting Checklist)
- SECONDARY_QUICK_REFERENCE.md (Emergency Procedures)

---

**Last Updated:** 2025-11-28
**Documentation Set Version:** 1.0
**Project:** MAMcrawler
