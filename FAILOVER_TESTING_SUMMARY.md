# qBittorrent Failover Testing - Complete Guide

## Quick Start

```bash
# 1. Ensure both qBittorrent instances are running
python monitor_qbittorrent_health.py

# 2. Run automated test suite (safe - only Tests 1, 3, 5)
python test_failover.py --quick

# 3. For full testing (requires VPN manipulation)
python test_failover.py

# 4. Record results
# Fill out FAILOVER_TEST_REPORT_TEMPLATE.md
```

---

## Files Created

| File | Purpose | When to Use |
|------|---------|-------------|
| **FAILOVER_TESTING_PROCEDURES.md** | Complete testing documentation | Read first for full context |
| **TEST_MAGNETS.txt** | Test magnet links and hash values | Reference during testing |
| **FAILOVER_TEST_REPORT_TEMPLATE.md** | Structured report template | Fill out after each test session |
| **test_failover.py** | Automated testing script | Run tests programmatically |
| **FAILOVER_TESTING_SUMMARY.md** | This file - quick reference | Quick start and overview |

---

## Test Overview

### TEST 1: Normal Operation (VPN Up)
**What it tests:** Primary instance is used when VPN is connected and both instances are healthy.

**Duration:** ~2 minutes
**Requires manual action:** No
**Safe to run:** Yes

**Success criteria:**
- All 5 magnets added successfully
- Magnets appear in primary instance (192.168.0.48:52095)
- No magnets in secondary or queue file

**Run command:**
```bash
python test_normal_operation.py
# OR
python test_failover.py --quick  # Includes Test 1, 3, 5
```

---

### TEST 2: VPN Down Failover
**What it tests:** Automatic failover to secondary instance when VPN disconnects.

**Duration:** ~5 minutes
**Requires manual action:** Yes (VPN disconnect/reconnect)
**Safe to run:** Yes (but disrupts VPN)

**Success criteria:**
- VPN detected as down
- Primary marked as VPN_DOWN
- All 3 magnets added to secondary instance
- No queue file created

**Manual steps:**
1. Run test script
2. Disconnect ProtonVPN when prompted
3. Wait for test to complete
4. Reconnect ProtonVPN when prompted

**Run command:**
```bash
python test_vpn_failover.py
# OR
python test_failover.py  # Full suite
```

---

### TEST 3: Manual Primary Block
**What it tests:** Fallback to secondary when primary is blocked by firewall.

**Duration:** ~3 minutes
**Requires manual action:** Yes (firewall rule creation/removal)
**Safe to run:** Yes

**Success criteria:**
- Primary blocked by firewall (TIMEOUT)
- Magnet added to secondary successfully
- Firewall rule removed cleanly

**Manual steps:**
1. Create firewall block rule (PowerShell as Admin):
   ```powershell
   New-NetFirewallRule -DisplayName "TEST: Block qBittorrent Primary" `
     -Direction Outbound -Protocol TCP -RemotePort 52095 `
     -RemoteAddress 192.168.0.48 -Action Block
   ```
2. Run test
3. Remove firewall rule when prompted:
   ```powershell
   Remove-NetFirewallRule -DisplayName "TEST: Block qBittorrent Primary"
   ```

**Run command:**
```bash
python test_manual_block.py
# OR
python test_failover.py --quick
```

---

### TEST 4: All Services Down (Queue Creation)
**What it tests:** Queue file creation when both instances unavailable.

**Duration:** ~2 minutes
**Requires manual action:** Yes (stop both instances)
**Safe to run:** Yes

**Success criteria:**
- Both instances detected as down
- All 3 magnets queued (0 added immediately)
- Queue file created with correct JSON structure
- No errors during workflow

**Manual steps:**
1. Disconnect ProtonVPN
2. Stop local qBittorrent: `Stop-Process -Name qbittorrent -Force`
3. Run test
4. Leave services down for Test 5

**Run command:**
```bash
python test_queue_creation.py
# OR
python test_failover.py  # Full suite
```

---

### TEST 5: Queue File Processing (Recovery)
**What it tests:** Queued magnets are processed when services restore.

**Duration:** ~3 minutes
**Requires manual action:** Yes (start one instance)
**Safe to run:** Yes

**Success criteria:**
- At least one instance restored
- All queued magnets processed successfully
- Queue file automatically deleted
- Torrents visible in qBittorrent Web UI

**Manual steps:**
1. Ensure queue file exists (from Test 4)
2. Start at least one qBittorrent instance:
   - Option A: Reconnect VPN for primary
   - Option B: Start local qBittorrent for secondary
3. Run test
4. Verify queue file deleted

**Run command:**
```bash
python test_queue_processing.py
# OR
python test_failover.py  # Full suite
```

---

## Test Modes

### Quick Mode (Recommended for Regular Testing)
**Tests Run:** 1, 3, 5
**Duration:** ~8 minutes
**VPN Manipulation:** None
**Best for:** Daily testing, CI/CD, quick validation

```bash
python test_failover.py --quick
```

### Skip Manual Mode
**Tests Run:** 1, 3, 5
**Duration:** ~8 minutes
**VPN Manipulation:** None
**Best for:** Automated testing without user interaction

```bash
python test_failover.py --skip-manual
```

### Full Mode (Comprehensive)
**Tests Run:** All (1, 2, 3, 4, 5)
**Duration:** ~20 minutes
**VPN Manipulation:** Yes (disconnect/reconnect required)
**Best for:** Pre-deployment validation, thorough testing

```bash
python test_failover.py
```

---

## Monitoring Commands

### Health Check
```bash
# Single check
python monitor_qbittorrent_health.py

# Continuous monitoring (every 30 seconds)
# PowerShell:
while ($true) { python monitor_qbittorrent_health.py; Start-Sleep 30 }
```

### Check VPN Status
```bash
# Check VPN adapter IP
ipconfig | findstr "10.2.0"
# Should show: 10.2.0.2

# Ping VPN gateway
ping 192.168.0.1
# Should succeed if VPN connected
```

### Check qBittorrent Instances
```bash
# Check primary
curl http://192.168.0.48:52095/api/v2/app/webapiVersion

# Check secondary
curl http://localhost:52095/api/v2/app/webapiVersion

# Check if local qBittorrent running
Get-Process qbittorrent
```

### Check Queue File
```bash
# Check if exists
dir qbittorrent_queue.json

# View contents
type qbittorrent_queue.json

# Count magnets
type qbittorrent_queue.json | findstr "magnet"
```

---

## Expected Test Results

### Healthy System (All Tests Pass)

```
======================================================================
qBittorrent Failover System - Automated Test Suite
======================================================================

Test Mode: quick
Primary URL: http://192.168.0.48:52095/
Secondary URL: http://localhost:52095/

TEST 1: Normal Operation (VPN Up)
  Successfully Added: 5
  Instance Used: primary
  TEST 1: PASS

TEST 3: Manual Primary Block
  Successfully Added: 1
  Instance Used: secondary
  TEST 3: PASS

TEST 5: Queue File Processing
  Successfully Recovered: 3
  Queue file cleaned up successfully
  TEST 5: PASS

======================================================================
FAILOVER TEST SUITE SUMMARY
======================================================================
Total Tests Defined: 5
Tests Run: 3
Tests Skipped: 2
Passed: 3
Failed: 0
Pass Rate: 100.0%
======================================================================
```

### System with Issues (Example)

```
TEST 1: FAIL
  Expected 5 successful, got 0
  Primary: HTTP_403 (IP not whitelisted)

TEST 3: FAIL
  Secondary: TIMEOUT (not running)

TEST 5: PASS
  (Processed queue successfully)

======================================================================
Total Tests Run: 3
Passed: 1
Failed: 2
Pass Rate: 33.3%
======================================================================
```

---

## Common Issues and Fixes

### Issue: Primary Returns HTTP 403
**Symptom:** Test 1 fails, primary shows HTTP_403

**Fix:**
```bash
# SSH/RDP to remote server (192.168.0.48)
# Update qBittorrent Web UI IP whitelist
# Add your VPN IP or use 0.0.0.0/0 (less secure)
```

### Issue: Secondary Not Running
**Symptom:** Test 3 fails, secondary shows TIMEOUT

**Fix:**
```powershell
# Start local qBittorrent
Start-Process "C:\Program Files\qBittorrent\qbittorrent.exe"

# Wait 10 seconds
Start-Sleep 10

# Verify running
Get-Process qbittorrent
```

### Issue: VPN Won't Disconnect
**Symptom:** Test 2 shows VPN still connected

**Fix:**
```bash
# Close ProtonVPN app completely
# Restart ProtonVPN app
# Manually disconnect before running test
```

### Issue: Queue File Not Created
**Symptom:** Test 4 fails, no queue file

**Fix:**
```bash
# Verify both services actually down
python monitor_qbittorrent_health.py
# Should show both as down

# Check file permissions
# Ensure write access to project directory
```

### Issue: Queue File Not Deleted
**Symptom:** Test 5 completes but file remains

**Fix:**
```bash
# Manually delete queue file
del qbittorrent_queue.json

# Check for magnets that couldn't be added
type qbittorrent_queue.json
# Fix underlying issue, then retry
```

---

## Safety Checklist

Before running tests, verify:

- [ ] **VPN Configured**
  - ProtonVPN installed
  - Can connect/disconnect safely
  - Port proxy configured (if needed)

- [ ] **Instances Accessible**
  - Primary responds: `curl http://192.168.0.48:52095/api/v2/app/webapiVersion`
  - Secondary responds: `curl http://localhost:52095/api/v2/app/webapiVersion`

- [ ] **Credentials Correct**
  - `.env` has `QBITTORRENT_URL`
  - `.env` has `QBITTORRENT_SECONDARY_URL`
  - Username/password match both instances

- [ ] **Disk Space Available**
  - At least 10GB free on F:\ drive
  - Test magnets are small but need allocation space

- [ ] **No Critical Downloads**
  - Pause any important ongoing downloads
  - Tests may disrupt active torrents

- [ ] **Admin Access Available**
  - Can run PowerShell as Administrator
  - Needed for firewall rule manipulation

---

## Post-Test Cleanup

After testing completes:

```bash
# 1. Remove all test torrents
# Via Web UI or API

# 2. Delete queue file if exists
del qbittorrent_queue.json

# 3. Remove test firewall rules
Remove-NetFirewallRule -DisplayName "TEST: Block qBittorrent Primary"

# 4. Reconnect VPN if disconnected
# Open ProtonVPN app -> Connect

# 5. Verify system health
python monitor_qbittorrent_health.py
```

---

## Reporting Results

### For Each Test Session

1. **Run Tests**
   ```bash
   python test_failover.py --quick
   # OR
   python test_failover.py  # Full suite
   ```

2. **Review JSON Report**
   - Check `failover_test_report_YYYYMMDD_HHMMSS.json`
   - Contains detailed results and metrics

3. **Fill Out Template**
   - Open `FAILOVER_TEST_REPORT_TEMPLATE.md`
   - Fill in test results, observations, issues
   - Save as `FAILOVER_TEST_REPORT_YYYYMMDD.md`

4. **Archive Results**
   - Move completed reports to `test_reports/` folder
   - Keep JSON files for historical tracking

---

## Integration with Workflow

The failover system is already integrated into `execute_full_workflow.py` Phase 5:

```python
# Phase 5: Add to qBittorrent (lines 370-469)
async with ResilientQBittorrentClient(
    primary_url=self.qb_url,
    secondary_url=self.qb_secondary_url,
    username=self.qb_user,
    password=self.qb_pass,
    queue_file="qbittorrent_queue.json",
    savepath=str(self.download_path)
) as client:
    # Automatic health check
    health = await client.perform_health_check()

    # Automatic failover if primary down
    successful, failed, queued = await client.add_torrents_with_fallback(
        magnet_links[:max_downloads]
    )
```

**No code changes needed** - just configure environment variables:

```bash
# .env
QBITTORRENT_URL=http://192.168.0.48:52095/
QBITTORRENT_SECONDARY_URL=http://localhost:52095/
QBITTORRENT_USERNAME=TopherGutbrod
QBITTORRENT_PASSWORD=Tesl@ismy#1
```

---

## Performance Benchmarks

Expected performance metrics:

| Metric | Target | Acceptable | Needs Investigation |
|--------|--------|------------|---------------------|
| Health check time | <1s | <3s | >5s |
| Primary connection | <500ms | <2s | >5s |
| Secondary connection | <200ms | <1s | >3s |
| Failover time | <5s | <10s | >15s |
| Queue processing | <3s | <10s | >30s |
| Overall test suite | <20min | <30min | >45min |

---

## Next Steps

1. **Initial Testing**
   ```bash
   # Run quick mode first
   python test_failover.py --quick
   ```

2. **Review Results**
   - Check JSON report
   - Verify all tests passed
   - Review any warnings

3. **Full Testing** (if quick mode passes)
   ```bash
   # Run full suite
   python test_failover.py
   ```

4. **Document Results**
   - Fill out `FAILOVER_TEST_REPORT_TEMPLATE.md`
   - Note any issues or observations
   - Save for future reference

5. **Integration Testing**
   ```bash
   # Test with actual workflow
   python execute_full_workflow.py
   ```

6. **Production Monitoring**
   ```bash
   # Set up continuous health monitoring
   # Run every 5 minutes via Task Scheduler
   python monitor_qbittorrent_health.py
   ```

---

## Support

If tests fail or unexpected behavior occurs:

1. **Check Health Status**
   ```bash
   python monitor_qbittorrent_health.py
   ```

2. **Review Logs**
   - Check `real_workflow_execution.log`
   - Check `failover_test_execution.log`

3. **Verify Configuration**
   - Check `.env` file
   - Verify both instances running
   - Test VPN connectivity

4. **Consult Documentation**
   - `QBITTORRENT_REDUNDANCY_SETUP.md` - Setup guide
   - `FAILOVER_TESTING_PROCEDURES.md` - Detailed procedures
   - Troubleshooting sections in both files

5. **Create Issue**
   - Include test report JSON
   - Include health check output
   - Include relevant log excerpts

---

## Quick Reference

```bash
# Health check
python monitor_qbittorrent_health.py

# Quick test (safe)
python test_failover.py --quick

# Full test (requires VPN manipulation)
python test_failover.py

# View queue file
type qbittorrent_queue.json

# Start secondary instance
Start-Process "C:\Program Files\qBittorrent\qbittorrent.exe"

# Check VPN
ping 192.168.0.1

# Reconnect VPN
# Open ProtonVPN app -> Connect
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-28
**Maintained By:** MAMcrawler Project
