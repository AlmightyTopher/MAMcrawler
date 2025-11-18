# Option B Setup - Dual Scraper Without SOCKS5

## How It Works

Instead of using SOCKS5 proxy, we use **Split Tunneling Exclude mode**:

```
System Python (C:\Program Files\Python311\python.exe)
  → NOT in excluded apps
  → All traffic goes through ProtonVPN
  → Appears as VPN IP to Goodreads

venv Python (C:\Users\dogma\Projects\MAMcrawler\venv\Scripts\python.exe)
  → Added to "Excluded Apps"
  → Bypasses VPN, uses direct WAN
  → Appears as your ISP IP to Goodreads
```

---

## Setup Steps (3 Minutes)

### 1. Change Split Tunneling Mode

1. Open **ProtonVPN**
2. Go to **Settings → Advanced → Split Tunneling**
3. Change mode to: **"Exclude selected apps from VPN tunnel"**
   - (This is the opposite of what we tried before)
4. Click **"Add Application"** or **"Manage Apps"**

### 2. Add venv Python to Excluded Apps

Add ONLY this path to excluded apps:
```
C:\Users\dogma\Projects\MAMcrawler\venv\Scripts\python.exe
```

**How to add:**
- Browse to the path and select `python.exe`
- Or paste the path if there's a text field

**Important:**
- ✅ Add: venv Python (will bypass VPN)
- ❌ Don't add: System Python (will use VPN)

### 3. Restart ProtonVPN

1. Disconnect from VPN server
2. Right-click system tray → **Exit**
3. Wait 10 seconds
4. Start ProtonVPN
5. **Connect to a VPN server** (important!)

### 4. Verify Setup

Run verification script:
```cmd
python verify_option_b.py
```

**Expected output:**
```
✅ System Python will use VPN
✅ venv Python will bypass VPN (direct WAN)
✅ Two different routes confirmed
```

### 5. Test Dual Scraper

```cmd
python run_dual_scraper.py
```

**Expected behavior:**
- Two Python processes launch
- VPN scraper uses system Python → VPN IP
- Direct scraper uses venv Python → Your ISP IP
- Both run simultaneously
- Results are merged

---

## File Structure

```
scraper_vpn.py          # VPN route scraper (run with system Python)
scraper_direct.py       # Direct route scraper (run with venv Python)
run_dual_scraper.py     # Orchestrator (launches both)
verify_option_b.py      # Verification script
```

---

## Verification

After setup, verify routes are different:

```cmd
# Check VPN scraper will use VPN
"C:\Program Files\Python311\python.exe" -c "import requests; print(requests.get('http://httpbin.org/ip').json())"

# Check Direct scraper will bypass VPN
venv\Scripts\python.exe -c "import requests; print(requests.get('http://httpbin.org/ip').json())"
```

**Expected:**
- System Python: Shows VPN IP (different from your ISP)
- venv Python: Shows your real ISP IP

**If both show VPN IP:** venv Python is not excluded, check Split Tunneling settings
**If both show ISP IP:** ProtonVPN is not connected or not working

---

## Troubleshooting

### "Both scrapers use same IP"
**Solution:**
- Verify Split Tunneling mode is "Exclude" (not "Include")
- Verify venv Python is in excluded apps list
- Restart ProtonVPN completely

### "Can't find system Python"
**Solution:**
- Edit `run_dual_scraper.py` line 24
- Change to your system Python path (run `where python` to find)

### "venv Python not found"
**Solution:**
- Make sure you're in the MAMcrawler directory
- Verify venv exists: `dir venv\Scripts\python.exe`

---

## Advantages Over Option A (SOCKS5)

✅ **Simpler:** No SOCKS5 proxy configuration needed
✅ **Reliable:** Works with all ProtonVPN versions
✅ **Transparent:** No proxy errors or connection issues
✅ **Clean:** Entire process routes through VPN vs. direct
✅ **Easier debugging:** Can test each route independently

---

## Next Steps

1. [ ] Change Split Tunneling to "Exclude" mode
2. [ ] Add venv Python to excluded apps
3. [ ] Restart ProtonVPN and reconnect
4. [ ] Run `python verify_option_b.py`
5. [ ] Run `python run_dual_scraper.py`
6. [ ] Check logs: `scraper_vpn.log` and `scraper_direct.log`
