# WireGuard Python-Only VPN Setup - START HERE

## What You Have

A complete dual Goodreads scraper system with a dedicated WireGuard tunnel that routes **only Python traffic** through VPN while keeping all other Windows traffic on your normal ISP connection.

## What's Included

✅ **WireGuard Configuration** - Ready to install
✅ **Python Scrapers** - VPN route + Direct route  
✅ **Verification Script** - Tests if setup works
✅ **Complete Documentation** - Step-by-step guides
✅ **7 Simple Commands** - Copy-paste setup

## Quick Start (15 Minutes Total)

### Step 1: Prerequisites (1 minute)
- [ ] WireGuard installed: https://www.wireguard.com/install/
- [ ] Administrator PowerShell open (right-click → "Run as Administrator")

### Step 2: Copy & Run Setup Commands (5 minutes)
Open: **WIREGUARD_QUICK_START.md**

Copy-paste these 7 commands in order:
1. Copy config file
2. Install tunnel service
3. Start tunnel service
4. Get interface index (note the number!)
5. Set interface metric
6. Create firewall rules
7. Add route

**Important:** When you get the interface index in step 4, write it down and use it in steps 5 & 7.

### Step 3: Verify Setup (2 minutes)
```bash
python verify_wireguard.py
```

Should show:
```
✅ SUCCESS - Two different routes detected!
  Python traffic:  [VPN IP]
  Windows traffic: [Your ISP IP]
```

If you see TWO DIFFERENT IPs, you're done! ✅

### Step 4: Run Dual Scraper (7 minutes)
```bash
python run_dual_scraper.py
```

Results saved to: `merged_results_[timestamp].json`

## Documentation Guide

**For Quick Setup:** → `WIREGUARD_QUICK_START.md`

**For Step-by-Step with Details:** → `WIREGUARD_SETUP.md`

**For Checklist Format:** → `WIREGUARD_CHECKLIST.txt`

**For Complete Technical Details:** → `WIREGUARD_SUMMARY.md`

**For File List:** → `WIREGUARD_FILES_CREATED.txt`

## What Gets Created

```
System Python (C:\Program Files\Python311\python.exe)
  ↓
  Routes through WireGuard tunnel (10.2.0.2)
  ↓
  Appears as: VPN IP
  
venv Python (.\venv\Scripts\python.exe)
  ↓
  Also routes through WireGuard tunnel
  ↓
  Appears as: Same VPN IP
  
All Other Windows Traffic (browsers, apps, OS)
  ↓
  Routes through normal ISP connection
  ↓
  Appears as: Your regular ISP IP
```

## Result

✅ Both scrapers run in parallel (2x speed)
✅ Both have different fingerprints (user agents, headers, timing)
✅ Python traffic isolated to VPN
✅ Other Windows traffic unaffected
✅ Low rate limiting risk
✅ Fully automated setup

## Troubleshooting

### "Service not found" after install
→ See "Troubleshooting" section in `WIREGUARD_SETUP.md`

### "Interface not found"
→ Wait 10 seconds, then try again

### "Both IPs are the same"
→ Check firewall rules and interface metric (see WIREGUARD_SETUP.md)

## Next Steps

1. **Right now:** Open `WIREGUARD_QUICK_START.md`
2. **Copy-paste** the 7 PowerShell commands (Administrator PowerShell)
3. **Run:** `python verify_wireguard.py`
4. **If successful, run:** `python run_dual_scraper.py`

## Questions?

- **Setup issues:** See `WIREGUARD_SETUP.md` → "Troubleshooting"
- **Want different IPs:** See `WIREGUARD_SUMMARY.md` → "If You Want Different IPs"
- **Complete overview:** Read `WIREGUARD_SUMMARY.md`

---

## File Locations

All files are in: `C:\Users\dogma\Projects\MAMcrawler\`

**Config:**
- `TopherTek-Python-Tunnel.conf` (will be copied to C:\ProgramData\WireGuard\)

**Scripts:**
- `verify_wireguard.py` - Run after setup
- `scraper_vpn.py` - VPN route scraper
- `scraper_direct.py` - Direct route scraper
- `run_dual_scraper.py` - Run both together

**Docs:**
- `WIREGUARD_QUICK_START.md` ← **READ THIS FIRST**
- `WIREGUARD_CHECKLIST.txt`
- `WIREGUARD_SETUP.md`
- `WIREGUARD_SUMMARY.md`

---

**Ready?** → Open `WIREGUARD_QUICK_START.md` and follow the 7 commands!
