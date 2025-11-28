# qBittorrent 403 Fix - Manual Step-by-Step Guide

## QUICK SUMMARY

Your qBittorrent Web UI is accessible at: **http://192.168.0.48:52095/**

The issue: IP whitelist is blocking API access from the client.

**Fix**: Remove IP whitelist restriction (takes 2 minutes)

---

## STEP 1: Open qBittorrent Web UI

1. Open a web browser (Chrome, Firefox, Edge, etc.)
2. Go to: **http://192.168.0.48:52095/**
3. You should see the login screen

---

## STEP 2: Log In

**Credentials:**
- Username: `TopherGutbrod`
- Password: `Tesl@ismy#1`

1. Enter username in the "Username" field
2. Enter password in the "Password" field
3. Click the login button (or press Enter)
4. You should now see the qBittorrent dashboard

---

## STEP 3: Open Settings

Once logged in, look for the menu. **The menu is usually in one of these locations:**

### Option A: Top Menu Bar
- Look for "Tools" in the top menu
- Click "Tools"
- Click "Options" or "Preferences"

### Option B: Settings/Gear Icon
- Look for a gear/cog icon in the top right or top left
- Click it to open options

### Option C: Side Menu
- Look for a sidebar on the left or right
- Find "Tools" or "Settings"
- Click it

### Option D: Direct URL (Fastest)
If you can't find the menu, try going directly to:
**http://192.168.0.48:52095/preferences**

---

## STEP 4: Find Web UI Settings

Once in the preferences/options:

1. Look for a list of categories on the left side
2. Find and click: **"Web UI"** (it's in the preferences categories list)
3. You should now see Web UI settings

---

## STEP 5: Fix the IP Whitelist

In the Web UI settings, look for one of these options:

### **Option A: "IP Whitelist" Field**
- Find the text field labeled "IP Whitelist" or "IP whitelist"
- If it contains IPs, **clear it completely** (delete all content)
- Leave the field empty
- Empty = allows all IPs

**OR**

### **Option B: "IP Whitelist Enabled" Checkbox**
- Find the checkbox labeled "IP Whitelist Enabled" or similar
- **Uncheck this box** to disable IP filtering
- This allows all IPs

**OR**

### **Option C: Add Your IP**
If you want to keep whitelisting but add your IP:
- Find the IP whitelist field
- Add: `127.0.0.1` (for local access)
- Or add: `192.168.1.0/24` (for your local network)

---

## STEP 6: Apply Changes

1. Look for an **"Apply"** button (or "OK", "Save")
2. Click it to save the changes
3. You may see a message like "Settings saved" or the page may refresh
4. **qBittorrent may need to reload** - this is normal

---

## STEP 7: Verify the Fix

After applying changes:

1. Go back to your terminal/command prompt
2. Run the workflow again:
   ```bash
   python execute_full_workflow.py
   ```

3. Watch for this message:
   ```
   [PHASE] PHASE 5: QBITTORRENT DOWNLOAD
   [OK] Added X torrents to qBittorrent
   ```

If you see `[OK]` instead of `[WARN] qBittorrent API returning 403`, **the fix worked!**

---

## TROUBLESHOOTING

### "I can't find Web UI settings"

Try this:
1. In the preferences/options list on the left, look for all items
2. Look for: "Web UI", "WebUI", "Web Interface", "Network", "Connection"
3. Click each one to check if it has IP whitelist settings

### "I cleared the field but still getting 403"

Try these steps:
1. Make sure you clicked **Apply** or **OK**
2. If there was a "Restart qBittorrent" message, restart it
3. Wait 5 seconds for settings to take effect
4. Try the workflow again

### "Can't find the IP Whitelist option"

Your qBittorrent version may have it in a different location:
1. Try looking under "Security" settings
2. Try "Connection" settings
3. Try searching the page with Ctrl+F for "whitelist"

### "qBittorrent keeps showing 403 after fix"

This could mean:
1. Settings didn't save properly - try again
2. Wrong qBittorrent instance - verify URL is 192.168.0.48:52095
3. Browser cache issue - try clearing cache or using incognito mode

---

## DETAILED SETTINGS REFERENCE

If you find the Web UI settings, here's what to look for:

```
[Web UI Settings]

☑ Enable Web User Interface          <- Should be checked
  HTTP Server

☑ HTTPS mode                          <- Can be checked or unchecked

Port: 52095                           <- Should be 52095

Bypass authentication for clients
☐ on localhost                        <- Optional

IP Whitelist                          <- **CLEAR THIS or DISABLE**
[                                    ]  <- Delete any IPs in here
                                        Or leave empty


IP Whitelist Enabled
☐ [Uncheck if present]               <- Disable IP filtering
```

---

## VIDEO TUTORIAL ALTERNATIVE

If you prefer visual instructions:

1. Open qBittorrent Web UI
2. Look at the page carefully
3. Find the settings option (gear icon or Tools menu)
4. Click Web UI settings
5. Find the IP whitelist field
6. Clear it or disable it
7. Click Apply
8. Done!

---

## FINAL CHECK

After applying changes, test that it works:

### Via Browser (Quick Test):
1. In qBittorrent Web UI
2. Add a torrent manually
3. If you can add it, the API is working

### Via Workflow (Complete Test):
```bash
python execute_full_workflow.py
```

Watch for Phase 5 to show `[OK]` instead of `[WARN]`

---

## IF ALL ELSE FAILS

If you still can't fix it via the Web UI:

1. **Try the config file modifier:**
   ```bash
   python qbittorrent_config_modifier.py
   ```

2. **Use Prowlarr fallback:**
   The workflow already has a fallback to use Prowlarr to add torrents instead

3. **Manual magnet links:**
   The workflow will prepare magnet links you can add manually:
   ```
   magnet:?xt=urn:btih:XXXX...
   ```

4. **Ask for help:**
   Check the QBITTORRENT_403_FIX_GUIDE.md for more details

---

## YOU GOT THIS!

The fix is literally just:
1. Open http://192.168.0.48:52095/
2. Log in
3. Find Web UI settings
4. Clear the IP whitelist field (or disable it)
5. Click Apply
6. Done!

Takes less than 2 minutes.
