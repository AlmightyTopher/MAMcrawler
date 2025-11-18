# Quick Configuration Guide

## 📅 Current Setup

- **Schedule:** Every **Friday** at 2am
- **Mode:** **WHITELIST** (only download selected genres)
- **Genres:** Science Fiction and Fantasy ONLY
- **Top N:** 10 **NEW** audiobooks per genre
- **Duplicate Detection:** Enabled (skips books already in qBittorrent)
- **Max Check:** Up to top 100 results to find 10 new books
- **qBittorrent:** Auto-add enabled (category: audiobooks-auto)

## 🎯 Adding More Genres

Edit `audiobook_auto_config.json`:

```json
{
  "included_genres": [
    "Science Fiction",
    "Fantasy",
    "SciFi",
    "Sci-Fi",
    "Mystery",        // Add new genre here
    "Thriller",       // Add another here
    "Horror"          // And another here
  ]
}
```

**Matching is case-insensitive and partial:**
- `"Science Fiction"` matches "Science Fiction", "Science Fiction & Fantasy", etc.
- `"SciFi"` matches "SciFi", "SciFi/Fantasy", etc.
- Include variations to catch all matches

## 🔄 Switching to Blacklist Mode

To download ALL genres EXCEPT certain ones:

```json
{
  "query_settings": {
    "use_whitelist": false,    // Changed from true to false
    ...
  },
  "excluded_genres": [
    "Romance",
    "Erotica",
    "Self-Help"
  ]
}
```

## ⚙️ Adjusting Download Amount

```json
{
  "query_settings": {
    "top_n_per_genre": 20,     // Changed from 10 to 20
    ...
  }
}
```

- **5-10:** Conservative, curated selection
- **10-20:** Balanced variety
- **20-50:** Aggressive collection

## 🔍 Duplicate Detection Settings

### Current Setup (Enabled)

```json
{
  "query_settings": {
    "skip_duplicates": true,     // Checks Audiobookshelf for duplicates
    "max_check_limit": 100       // Checks up to top 100 to find NEW books
  }
}
```

### How It Works

**System automatically:**
1. Connects to your Audiobookshelf library (836+ audiobooks)
2. Queries Science Fiction and Fantasy genres
3. Compares each result against your library
4. **Skips books you already have**
5. Continues checking until 10 NEW books found
6. Stops after checking top 100 (configurable)

**Example:**
- Website has 200 SciFi audiobooks
- You already have 50 of them in Audiobookshelf
- System checks top 100 results
- Finds 10 NEW books you don't have
- Adds only those 10 to qBittorrent
- Report shows: "Skipped 40 duplicates, added 10 new books"

### Adjust Max Check Limit

If you have a HUGE library (500+ books):

```json
{
  "query_settings": {
    "max_check_limit": 200     // Check up to top 200 to find 10 new
  }
}
```

**When to increase:**
- Mature library with 500+ SciFi/Fantasy books
- System finding fewer than 10 new books per genre
- Want to dig deeper into catalog

### Disable Duplicate Detection

```json
{
  "query_settings": {
    "skip_duplicates": false    // Download top 10 regardless
  }
}
```

**When to disable:**
- Testing the system
- Want to re-download everything
- Audiobookshelf not accessible

**See:** `DUPLICATE_DETECTION_GUIDE.md` for full details

## 📆 Changing Schedule Day/Time

### Option 1: Edit Config (informational only)
```json
{
  "schedule": {
    "day_of_week": "sunday",    // Changed to Sunday
    "time": "03:00"              // Changed to 3am
  }
}
```

### Option 2: Update Windows Task (REQUIRED)

Re-run the setup script:

```powershell
.\setup_weekly_schedule.ps1 -DayOfWeek "Sunday" -Time "03:00"
```

Or manually in Task Scheduler:
1. Open Task Scheduler
2. Find "AudiobookWeeklyBatch"
3. Right-click → Properties
4. Go to Triggers tab
5. Edit the trigger
6. Change day/time

## 🧪 Testing Your Changes

Always test with dry-run after making config changes:

```bash
python audiobook_auto_batch.py --dry-run
```

Check the output:
- ✅ Whitelisted genres showing correctly?
- ✅ Top N amount correct?
- ✅ Results look good?

Then run for real:
```bash
python audiobook_auto_batch.py
```

## 🎛️ MAM-Specific Settings

Based on MAM guides, these settings optimize for ratio:

```json
{
  "download_settings": {
    "prefer_freeleech": true,        // Prioritize Staff Freeleech torrents
    "prefer_vip_torrents": true,     // Prioritize VIP torrents (always freeleech for VIP)
    "use_freeleech_wedges": true     // Use FL wedges on non-freeleech torrents
  }
}
```

**Your Stats (from MAM guides):**
- Ratio: 4.053602 (way above minimum!)
- Bonus Points: 99,999 (MAXED - use them!)
- FL Wedges: 110
- Earning: 1,413 points/hour

**Recommendation:**
- Trade 50,000-90,000 bonus points for upload credit
- Use FL wedges liberally (you earn more than you use)
- Download VIP torrents preferentially (always freeleech for you)

## 📊 Common Configurations

### Conservative (Quality over Quantity)
```json
{
  "query_settings": {
    "top_n_per_genre": 5,
    "use_whitelist": true
  },
  "included_genres": ["Science Fiction", "Fantasy"]
}
```

### Balanced (Current Setup)
```json
{
  "query_settings": {
    "top_n_per_genre": 10,
    "use_whitelist": true
  },
  "included_genres": ["Science Fiction", "Fantasy", "SciFi", "Sci-Fi"]
}
```

### Aggressive (Everything Except...)
```json
{
  "query_settings": {
    "top_n_per_genre": 20,
    "use_whitelist": false
  },
  "excluded_genres": ["Romance", "Erotica", "Self-Help", "Children"]
}
```

## 🚀 Quick Commands

```bash
# Test with dry-run
python audiobook_auto_batch.py --dry-run

# Run for real
python audiobook_auto_batch.py

# Show available genres
python audiobook_query.py genres

# Show timespans
python audiobook_query.py timespans

# Refresh filters from website
python audiobook_query.py refresh

# Setup/update weekly schedule (as Admin)
.\setup_weekly_schedule.ps1

# Manual test run via Task Scheduler
schtasks /Run /TN "AudiobookWeeklyBatch"

# Check last run status
Get-ScheduledTask -TaskName "AudiobookWeeklyBatch"
```

## 📁 Important Files

- **`audiobook_auto_config.json`** - Main configuration (edit this!)
- **`audiobook_auto.log`** - Execution log
- **`batch_report_*.txt`** - Summary reports
- **`catalog_cache/genres.json`** - Available genres
- **`catalog_cache/timespans.json`** - Available timespans

## ⚠️ Troubleshooting

### "No genres/timespans found"
```bash
python audiobook_catalog_crawler.py
```

### "Not in whitelist" but should be
Check spelling and case in `included_genres`. Matching is case-insensitive but must be substring match.

### Downloaded wrong genres
Check `audiobook_auto.log` for which genres were processed. Verify `use_whitelist` is set correctly.

### Task not running
1. Check Task Scheduler → AudiobookWeeklyBatch → History
2. Check `audiobook_auto.log` for errors
3. Verify qBittorrent is running at scheduled time

## 💡 Pro Tips

1. **Always dry-run after config changes** to verify behavior
2. **Keep backups of your config** before major changes
3. **Check logs weekly** to ensure automation is working
4. **Trade bonus points regularly** (yours are capped!)
5. **Use your 110 FL wedges** liberally - they regenerate

---

**Current Status:** Ready to run every Friday at 2am, downloading top 10 Science Fiction and Fantasy audiobooks!
