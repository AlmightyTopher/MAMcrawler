# qBittorrent Failover System Test Report

## Test Session Information

**Test Date:** _____________________
**Test Time:** _____________________
**Tester:** _____________________
**System:** Windows _____
**Python Version:** _____
**Git Branch/Commit:** _____________________

---

## Environment Status (Pre-Test)

### VPN Configuration

- [ ] ProtonVPN installed and configured
- [ ] VPN adapter IP: `10.2.0.2` (Actual: ____________)
- [ ] Gateway reachable: `ping 192.168.0.1` → **Success** / **Fail**
- [ ] Port proxy configured: `netsh interface portproxy show all` → **OK** / **Not OK**

**Notes:**
___________________________________________________________________________

### Primary Instance (192.168.0.48:52095)

- [ ] Instance accessible
- [ ] Web UI responds: `curl http://192.168.0.48:52095/api/v2/app/webapiVersion`
  - Response: _____________________
- [ ] Authentication successful
- [ ] Download path verified: `F:\Audiobookshelf\Books`
- [ ] Category 'audiobooks' exists

**Notes:**
___________________________________________________________________________

### Secondary Instance (localhost:52095)

- [ ] Instance running: `Get-Process qbittorrent`
- [ ] Web UI accessible: `curl http://localhost:52095/api/v2/app/webapiVersion`
  - Response: _____________________
- [ ] Same credentials as primary: **Yes** / **No**
- [ ] Same download path: **Yes** / **No**
- [ ] Category 'audiobooks' exists

**Notes:**
___________________________________________________________________________

### System Configuration

- [ ] `.env` file has `QBITTORRENT_URL`
- [ ] `.env` file has `QBITTORRENT_SECONDARY_URL`
- [ ] Python venv activated
- [ ] `monitor_qbittorrent_health.py` available
- [ ] `test_failover.py` script available

**Notes:**
___________________________________________________________________________

---

## TEST 1: Normal Operation (VPN Up)

**Objective:** Verify primary instance is used when VPN is up and both instances are healthy.

### Pre-Test State

- VPN Status: **Connected** / **Disconnected**
- Primary Health: _____________________
- Secondary Health: _____________________
- Queue file exists: **Yes** / **No**

### Execution

**Command:** `python test_normal_operation.py`

**Start Time:** _____________________
**End Time:** _____________________
**Duration:** __________ seconds

### Results

- Magnets Attempted: **5**
- Magnets Succeeded: _____
- Magnets Failed: _____
- Magnets Queued: _____
- Instance Used: **Primary** / **Secondary** / **Queued**

### Verification Checklist

- [ ] All 5 torrents visible in primary Web UI
- [ ] Category set to 'audiobooks'
- [ ] Save path correct: `F:\Audiobookshelf\Books`
- [ ] No queue file created
- [ ] Torrents NOT in secondary instance

### Output Log

```
[Paste relevant test output here]




```

### Status

**PASS** / **FAIL**

### Notes

___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________

---

## TEST 2: VPN Down Failover

**Objective:** Verify automatic failover to secondary when VPN disconnects.

### Pre-Test State

- VPN Status: **Connected** / **Disconnected**
- Primary Health: _____________________
- Secondary Health: _____________________

### VPN Disconnect Action

- Disconnect Method: **ProtonVPN app** / **Other:** _____________________
- Disconnect Time: _____________________
- Verification: `ping 192.168.0.1` → **Timeout** / **Success** / **Other:** _____

### Execution

**Command:** `python test_vpn_failover.py`

**Start Time:** _____________________
**End Time:** _____________________
**Duration:** __________ seconds

### Results

- Magnets Attempted: **3**
- Magnets Succeeded: _____
- Magnets Failed: _____
- Magnets Queued: _____
- Instance Used: **Primary** / **Secondary** / **Queued**

### Verification Checklist

- [ ] VPN detected as down by health check
- [ ] Primary marked as `VPN_DOWN`
- [ ] All 3 torrents in secondary Web UI
- [ ] No torrents in primary Web UI
- [ ] No queue file created

### VPN Reconnect

- Reconnect Time: _____________________
- Health check after reconnect:
  - Primary: _____________________
  - Secondary: _____________________

### Output Log

```
[Paste relevant test output here]




```

### Status

**PASS** / **FAIL**

### Notes

___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________

---

## TEST 3: Manual Primary Block

**Objective:** Verify fallback when primary is blocked by firewall but VPN is up.

### Pre-Test State

- Firewall rule created: **Yes** / **No**
- Primary accessible before block: **Yes** / **No**
- Secondary accessible: **Yes** / **No**

**Firewall Rule Command Used:**
```
___________________________________________________________________________
```

### Execution

**Command:** `python test_manual_block.py`

**Start Time:** _____________________
**End Time:** _____________________
**Duration:** __________ seconds

### Results

- Magnets Attempted: **1**
- Magnets Succeeded: _____
- Instance Used: **Primary** / **Secondary** / **Queued**

### Verification Checklist

- [ ] Primary blocked by firewall (TIMEOUT or ERROR)
- [ ] Magnet added to secondary successfully
- [ ] Firewall rule removed successfully
- [ ] Primary accessible after rule removal

### Output Log

```
[Paste relevant test output here]




```

### Status

**PASS** / **FAIL**

### Notes

___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________

---

## TEST 4: All Services Down (Queue Creation)

**Objective:** Verify queue file creation when both instances are unavailable.

### Pre-Test State

- VPN: **Connected** / **Disconnected**
- Primary qBittorrent: **Running** / **Stopped**
- Secondary qBittorrent: **Running** / **Stopped**
- Queue file exists: **Yes** / **No** (should be No before test)

### Service Shutdown

- VPN disconnected: _____________________
- Secondary qBittorrent stopped: _____________________
- Both services down confirmed: **Yes** / **No**

**Commands Used to Stop Services:**
```
___________________________________________________________________________
```

### Execution

**Command:** `python test_queue_creation.py`

**Start Time:** _____________________
**End Time:** _____________________
**Duration:** __________ seconds

### Results

- Magnets Attempted: **3**
- Magnets Succeeded: _____
- Magnets Failed: _____
- Magnets Queued: _____

### Queue File Verification

- [ ] File created at `qbittorrent_queue.json`
- [ ] Contains 3 magnet links
- [ ] JSON structure valid
- [ ] `saved_at` timestamp present
- [ ] `reason` field populated
- [ ] `instructions` field present

**Queue File Content Preview:**
```json
[Paste first 15 lines of qbittorrent_queue.json]






```

### Output Log

```
[Paste relevant test output here]




```

### Status

**PASS** / **FAIL**

### Notes

___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________

---

## TEST 5: Queue File Processing (Recovery)

**Objective:** Verify queued magnets are automatically processed when services restore.

### Pre-Test State

- Queue file exists: **Yes** / **No** (should be Yes from Test 4)
- Magnets in queue: _____ (should be 3)
- Services to restore: **Primary** / **Secondary** / **Both**

### Service Restoration

- VPN reconnected: _____________________ (if applicable)
- Secondary qBittorrent started: _____________________ (if applicable)
- Health check result:
  - Primary: _____________________
  - Secondary: _____________________

**Commands Used to Restore Services:**
```
___________________________________________________________________________
```

### Execution

**Command:** `python test_queue_processing.py`

**Start Time:** _____________________
**End Time:** _____________________
**Duration:** __________ seconds

### Results

- Magnets in Queue Before: _____
- Magnets Recovered: _____
- Magnets Failed: _____
- Instance Used: **Primary** / **Secondary**

### Verification Checklist

- [ ] All queued magnets processed successfully
- [ ] Queue file deleted automatically
- [ ] Torrents visible in qBittorrent Web UI
- [ ] No errors during processing
- [ ] Correct instance used (primary or secondary)

### Output Log

```
[Paste relevant test output here]




```

### Status

**PASS** / **FAIL**

### Notes

___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________

---

## Performance Metrics

### Response Times

- Health check average: __________ ms
- Primary instance connection: __________ ms
- Secondary instance connection: __________ ms
- Failover time (primary → secondary): __________ seconds
- Queue processing time: __________ seconds

### Success Rates

- Total magnets attempted across all tests: _____
- Successfully added (primary): _____
- Successfully added (secondary): _____
- Queued to file: _____
- Failed completely: _____
- **Overall success rate:** _____%

**Calculation:** (successful + queued) / total attempted × 100

---

## Issues Encountered

### Critical Issues

**Issue #1:**
- Description: ___________________________________________________________________________
- Test Affected: _____________________
- Impact: **High** / **Medium** / **Low**
- Resolution: ___________________________________________________________________________

**Issue #2:**
- Description: ___________________________________________________________________________
- Test Affected: _____________________
- Impact: **High** / **Medium** / **Low**
- Resolution: ___________________________________________________________________________

### Warnings

**Warning #1:**
- Description: ___________________________________________________________________________
- Test Affected: _____________________
- Impact: **Minor** / **Informational**

**Warning #2:**
- Description: ___________________________________________________________________________
- Test Affected: _____________________
- Impact: **Minor** / **Informational**

### Unexpected Behavior

**Behavior #1:**
- What happened: ___________________________________________________________________________
- Expected behavior: ___________________________________________________________________________
- Actual behavior: ___________________________________________________________________________
- Reproducible: **Yes** / **No**

---

## Recommendations

### System Improvements

1. ___________________________________________________________________________
2. ___________________________________________________________________________
3. ___________________________________________________________________________

### Documentation Updates

1. ___________________________________________________________________________
2. ___________________________________________________________________________
3. ___________________________________________________________________________

### Future Tests

1. ___________________________________________________________________________
2. ___________________________________________________________________________
3. ___________________________________________________________________________

---

## Overall Test Summary

**Total Tests Run:** 5
**Tests Passed:** _____
**Tests Failed:** _____
**Tests Skipped:** _____
**Pass Rate:** _____%

**System Readiness Assessment:**

- [ ] **Ready for Production** - All tests passed, no critical issues
- [ ] **Needs Minor Fixes** - Some tests failed but workarounds exist
- [ ] **Requires Re-test** - Critical issues found, fixes needed before production
- [ ] **Not Ready** - Multiple failures, significant issues detected

**Justification:**
___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________

---

## Action Items

### Immediate Actions Required

- [ ] Action: ___________________________________________________________________________
  - Owner: _____________________
  - Due Date: _____________________

- [ ] Action: ___________________________________________________________________________
  - Owner: _____________________
  - Due Date: _____________________

### Follow-up Actions

- [ ] Action: ___________________________________________________________________________
  - Owner: _____________________
  - Due Date: _____________________

- [ ] Action: ___________________________________________________________________________
  - Owner: _____________________
  - Due Date: _____________________

---

## Tester Sign-off

**Name:** _____________________
**Date:** _____________________
**Signature:** _____________________

**Reviewer (if applicable):**
**Name:** _____________________
**Date:** _____________________
**Signature:** _____________________

---

## Appendix A: System Configuration

**Environment Variables (.env):**
```
QBITTORRENT_URL=___________________________________________________________________________
QBITTORRENT_SECONDARY_URL=___________________________________________________________________________
QBITTORRENT_USERNAME=___________________________________________________________________________
QBITTORRENT_PASSWORD=[REDACTED]
```

**Network Configuration:**
```
VPN Adapter IP: ___________________________________________________________________________
VPN Gateway: ___________________________________________________________________________
Port Proxy: ___________________________________________________________________________
```

**qBittorrent Versions:**
- Primary Instance: ___________________________________________________________________________
- Secondary Instance: ___________________________________________________________________________

---

## Appendix B: Log Excerpts

### Test 1 Complete Log

```
[Paste complete test output if helpful]













```

### Test 2 Complete Log

```
[Paste complete test output if helpful]













```

### Test 3 Complete Log

```
[Paste complete test output if helpful]













```

### Test 4 Complete Log

```
[Paste complete test output if helpful]













```

### Test 5 Complete Log

```
[Paste complete test output if helpful]













```

---

## Appendix C: Health Check Results

**Pre-Test Health Check:**
```
[Paste monitor_qbittorrent_health.py output from before testing]






```

**Post-Test Health Check:**
```
[Paste monitor_qbittorrent_health.py output from after testing]






```

---

**Report Version:** 1.0
**Template Last Updated:** 2025-11-28
**Generated By:** MAMcrawler Failover Testing Suite
