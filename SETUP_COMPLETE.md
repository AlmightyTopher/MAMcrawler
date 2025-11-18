# ✅ Setup Complete - Friday SciFi/Fantasy Automated Downloads

## 🎉 What's Been Configured

### 📅 Schedule
- **Day:** Friday (changed from Monday)
- **Time:** 2:00 AM
- **Frequency:** Weekly

### 🎯 Genre Selection
- **Mode:** WHITELIST (only download selected genres)
- **Included Genres:**
  - Science Fiction
  - Fantasy
  - SciFi
  - Sci-Fi

### 📊 Download Settings
- **Top N per genre:** 10 audiobooks
- **qBittorrent category:** audiobooks-auto
- **Auto-add:** Enabled
- **Prefer freeleech:** Enabled
- **Prefer VIP torrents:** Enabled
- **Use FL wedges:** Enabled

## 📚 MAM Knowledge Acquired

### Your Current Stats (from scraped guides)
- **Ratio:** 4.053602 (excellent!)
- **Upload:** 1.833 TiB
- **Download:** 463.03 GiB
- **Bonus Points:** 99,999 (MAXED OUT!)
- **FL Wedges:** 110
- **Earning Rate:** 1,413.399 points/hour

### Key Findings from MAM Guides

**Bonus Points System:**
- Earn points by seeding after 72 hours
- 500 points = 1 GB upload credit
- 5,000 points = 28 days VIP status
- **Points cap at 99,999** (you're there!)

**Best Ratio Strategies:**

1. **VIP Torrents** (👑 BEST FOR YOU)
   - All VIP torrents are FREELEECH for VIP members
   - ~33% of all torrents
   - 0 bytes download - no ratio impact!

2. **Staff Freeleech Picks**
   - Available at: https://www.myanonamouse.net/freeleech.php
   - 0 bytes download
   - Hundreds of files from every category

3. **Freeleech Wedges**
   - You have 110 wedges
   - Use on large audiobooks
   - Regenerate via bonus points

4. **Trade Bonus Points for Upload Credit**
   - **URGENT:** You're capped at 99,999
   - Trade 50,000+ points NOW
   - Gain 100+ GB upload credit
   - Prevents wasting earned points

## 🚀 Immediate Action Items

### 1. ⚠️ USE YOUR BONUS POINTS (URGENT!)

You're at the 99,999 cap and earning 1,413 points/hour. You're **wasting points**!

**Go to:** https://www.myanonamouse.net/store.php

**Trade points for upload credit:**
- 50,000 points → 100 GB upload credit
- 90,000 points → 180 GB upload credit

This gives you a **massive ratio buffer** for guilt-free downloading!

### 2. 🧪 Test the Automated System

Run a dry-run test:

```bash
# Double-click this or run manually:
test_automated_batch.bat

# Or manually:
python audiobook_auto_batch.py --dry-run
```

**Check the output:**
- ✅ Shows "WHITELIST MODE: Only downloading Science Fiction, Fantasy, SciFi, Sci-Fi"
- ✅ Processing 1-2 matching genres
- ✅ Top 10 audiobooks per genre
- ✅ Lists what would be downloaded

### 3. 📋 Review the Dry-Run Results

Check these files:
- **`batch_report_*.txt`** - Summary of what would be downloaded
- **`audiobook_auto.log`** - Detailed execution log
- **`batch_stats_*.json`** - Machine-readable stats

### 4. ✅ Run For Real (First Time)

If dry-run looks good:

```bash
python audiobook_auto_batch.py
```

This will:
- Query Science Fiction and Fantasy genres
- Grab top 10 audiobooks from each
- Add them to qBittorrent automatically
- Save detailed report

### 5. 📅 Setup Weekly Schedule

Run PowerShell **as Administrator**:

```powershell
.\setup_weekly_schedule.ps1
```

This creates a Windows Task Scheduler task to run every Friday at 2am.

**Verify:**
```powershell
Get-ScheduledTask -TaskName "AudiobookWeeklyBatch"
```

## 📖 Documentation Created

### Core Guides
1. **`MAM_RATIO_STRATEGY.md`** - Complete guide to MAM bonus points & ratio optimization
2. **`QUICK_CONFIG_GUIDE.md`** - How to modify settings and add genres
3. **`AUTOMATED_BATCH_README.md`** - Full automated batch system documentation
4. **`AUDIOBOOK_CATALOG_README.md`** - Manual query interface guide

### Reference Files
- **`audiobook_auto_config.json`** - Main configuration file
- **`.env`** - qBittorrent credentials (already configured)

## 🎛️ Quick Reference

### Add More Genres Later

Edit `audiobook_auto_config.json`:

```json
{
  "included_genres": [
    "Science Fiction",
    "Fantasy",
    "SciFi",
    "Sci-Fi",
    "Mystery",        // Add here
    "Thriller"        // Add here
  ]
}
```

Then test:
```bash
python audiobook_auto_batch.py --dry-run
```

### Change Top N

Edit `audiobook_auto_config.json`:

```json
{
  "query_settings": {
    "top_n_per_genre": 20    // Changed from 10
  }
}
```

### Switch to Blacklist Mode

Edit `audiobook_auto_config.json`:

```json
{
  "query_settings": {
    "use_whitelist": false,    // Changed from true
    ...
  },
  "excluded_genres": [
    "Romance",
    "Erotica",
    "Self-Help"
  ]
}
```

## 📊 Expected Results

### Per Week (Science Fiction + Fantasy)
- **Genres processed:** 1-2 (depending on site categorization)
- **Audiobooks found:** 20-40 total
- **Top 10 selected:** 10-20 audiobooks
- **Added to qBittorrent:** 10-20 new downloads
- **Estimated size:** ~3-6 GB (at 300MB average)
- **Duration:** 5-15 minutes
- **Ratio impact:** ZERO (if using VIP/freeleech torrents)

### Per Month
- **~40-80 audiobooks** downloaded
- **~12-24 GB** per month
- **Still earning bonus points** from seeding
- **Ratio continues improving** from upload credits

## 🎯 Optimization Tips

### Maximize Freeleech Downloads

The automated system is configured to:

1. **Prefer VIP torrents** (`prefer_vip_torrents: true`)
   - All VIP = freeleech for you
   - No ratio impact

2. **Prefer freeleech** (`prefer_freeleech: true`)
   - Staff picks first
   - 0 bytes download

3. **Use FL wedges** (`use_freeleech_wedges: true`)
   - Apply to non-freeleech torrents
   - You have 110 wedges

### Trade Bonus Points Regularly

**Your schedule:**
- **Monday:** Check bonus points
- **If above 90,000:** Trade 50,000 for 100 GB upload credit
- **Friday 2am:** Automated batch runs
- **Saturday morning:** Review results

This ensures you never cap out and waste points.

## 🔍 Monitoring & Logs

### Check Automated Runs

**After each Friday run:**

1. **Open:** `batch_report_YYYYMMDD_HHMMSS.txt`
   - Shows what was downloaded
   - Success/failure counts
   - Any errors

2. **Review:** `audiobook_auto.log`
   - Detailed execution log
   - All queries and downloads
   - Debugging info

3. **Verify in qBittorrent:**
   - Category: "audiobooks-auto"
   - Should see new torrents from Friday

### Task Scheduler Status

```powershell
# Check task status
Get-ScheduledTask -TaskName "AudiobookWeeklyBatch"

# Check last run result
Get-ScheduledTaskInfo -TaskName "AudiobookWeeklyBatch"

# View history in Task Scheduler GUI
# Task Scheduler → AudiobookWeeklyBatch → History tab
```

## 🛠️ Troubleshooting

### "No genres/timespans found"

Run discovery first:
```bash
python audiobook_catalog_crawler.py
```

### Task didn't run at scheduled time

1. Check Task Scheduler history
2. Verify qBittorrent was running
3. Check `audiobook_auto.log`

### Wrong genres downloaded

1. Check `use_whitelist` is `true`
2. Verify `included_genres` spelling
3. Review `audiobook_auto.log` for filter results

## 📞 Support & Help

**Guides to reference:**
- MAM ratio strategies: `MAM_RATIO_STRATEGY.md`
- Config changes: `QUICK_CONFIG_GUIDE.md`
- Full system docs: `AUTOMATED_BATCH_README.md`

**Log files to check:**
- Execution log: `audiobook_auto.log`
- Summary reports: `batch_report_*.txt`
- Detailed stats: `batch_stats_*.json`

## 🎊 You're All Set!

**What happens next:**

1. **Now:** Trade your bonus points for upload credit
2. **Test:** Run dry-run to verify configuration
3. **Optional:** Run first real batch manually
4. **Setup:** Create weekly schedule (PowerShell as Admin)
5. **Friday 2am:** First automated run!
6. **Saturday:** Review results and enjoy new audiobooks!

**Every Friday at 2am**, your system will:
- Wake up automatically
- Query Science Fiction and Fantasy genres
- Grab top 10 from each
- Add to qBittorrent
- Generate detailed reports
- Go back to sleep

You wake up Saturday morning to fresh Science Fiction and Fantasy audiobooks! 🎧📚

---

**Welcome to automated audiobook bliss!** 🚀
