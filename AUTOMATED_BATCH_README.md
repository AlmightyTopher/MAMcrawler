# Automated Weekly Audiobook Batch Downloader

Automatically query all genres, grab top 10 audiobooks from each, and add them to qBittorrent every week.

## 🎯 What It Does

1. **Runs weekly** (configurable day/time)
2. **Queries all genres** (except excluded ones)
3. **Grabs top N audiobooks** per genre (default: 10)
4. **Automatically adds to qBittorrent**
5. **Generates reports** with stats and logs

## 📋 Quick Start

### 1. Configure Excluded Genres

Edit `audiobook_auto_config.json`:

```json
{
  "excluded_genres": [
    "Romance",
    "Erotica",
    "Self-Help"
  ]
}
```

Add any genres you want to skip. Matching is case-insensitive and partial.

### 2. Test with Dry-Run

Test without actually downloading:

```bash
python audiobook_auto_batch.py --dry-run
```

This will:
- Query all non-excluded genres
- Show what would be downloaded
- Generate a report
- Not actually add to qBittorrent

### 3. Run Manually (Real Mode)

Once you're happy with the dry-run results:

```bash
python audiobook_auto_batch.py
```

This will actually add audiobooks to qBittorrent.

### 4. Setup Weekly Schedule

Run the PowerShell setup script:

```powershell
# Run PowerShell as Administrator
.\setup_weekly_schedule.ps1

# Or customize day/time
.\setup_weekly_schedule.ps1 -DayOfWeek "Sunday" -Time "03:00"
```

This creates a Windows Task Scheduler task that runs automatically every week.

## ⚙️ Configuration

### `audiobook_auto_config.json`

```json
{
  "schedule": {
    "enabled": true,
    "frequency": "weekly",
    "day_of_week": "monday",      // Informational only
    "time": "02:00"                // Informational only
  },
  "query_settings": {
    "top_n_per_genre": 10,         // How many per genre
    "timespan_preference": "recent", // Prefer recent releases
    "skip_duplicates": true,       // Skip already downloaded
    "min_seeders": 5               // Minimum seeders (not implemented yet)
  },
  "excluded_genres": [
    "Romance",                     // Add genres to exclude here
    "Erotica",
    "Self-Help"
  ],
  "download_settings": {
    "auto_add_to_qbittorrent": true,  // Enable/disable qBittorrent
    "category": "audiobooks-auto",     // qBittorrent category
    "save_path": "",                   // Custom save path (optional)
    "dry_run": false                   // True = don't actually download
  },
  "notifications": {
    "enabled": true,
    "log_file": "audiobook_auto.log",
    "summary_report": true
  }
}
```

## 📊 Output & Reports

### Log File

`audiobook_auto.log` contains detailed execution logs:
- Every genre queried
- Every audiobook found
- Every download added
- Any errors encountered

### Summary Reports

After each run, generates:

**`batch_report_YYYYMMDD_HHMMSS.txt`** - Human-readable summary:
```
========================================
BATCH DOWNLOAD SUMMARY
========================================

Genres Processed:    15
Audiobooks Found:    150
Audiobooks Added:    120
Errors:              2
Skipped Genres:      3

DOWNLOADS:
  - [Mystery] The Silent Patient
  - [Thriller] Gone Girl
  - [SciFi] Project Hail Mary
  ...
```

**`batch_stats_YYYYMMDD_HHMMSS.json`** - Machine-readable stats:
```json
{
  "started_at": "2025-01-15T02:00:00",
  "completed_at": "2025-01-15T02:45:00",
  "genres_processed": 15,
  "audiobooks_found": 150,
  "audiobooks_added": 120,
  "downloads": [...],
  "errors": [...]
}
```

## 🔧 Advanced Usage

### Command-Line Options

```bash
# Dry-run mode
python audiobook_auto_batch.py --dry-run

# Custom config file
python audiobook_auto_batch.py --config my_config.json

# Both
python audiobook_auto_batch.py --dry-run --config my_config.json
```

### Change Top N Per Genre

Edit `audiobook_auto_config.json`:

```json
{
  "query_settings": {
    "top_n_per_genre": 5    // Changed from 10 to 5
  }
}
```

### Change Schedule Day/Time

Re-run the setup script with new parameters:

```powershell
.\setup_weekly_schedule.ps1 -DayOfWeek "Sunday" -Time "03:00"
```

Or manually edit in Task Scheduler:
1. Open Task Scheduler
2. Find "AudiobookWeeklyBatch"
3. Right-click → Properties → Triggers → Edit

### Add More Excluded Genres

Edit `audiobook_auto_config.json`:

```json
{
  "excluded_genres": [
    "Romance",
    "Erotica",
    "Self-Help",
    "Children",        // Added
    "Religious",       // Added
    "Poetry"           // Added
  ]
}
```

Partial matches work too:
- `"Teen"` excludes "Teen Fiction", "Teen Romance", etc.
- `"Young"` excludes "Young Adult", "Young Readers", etc.

### Disable Auto-Download (Query Only)

Set in config:

```json
{
  "download_settings": {
    "auto_add_to_qbittorrent": false
  }
}
```

This will query and generate reports without adding to qBittorrent.

### Custom qBittorrent Category

Set in config:

```json
{
  "download_settings": {
    "category": "audiobooks-auto"
  }
}
```

In qBittorrent:
1. Right-click in sidebar
2. Add category → "audiobooks-auto"
3. Set download path for this category

## 🛠️ Troubleshooting

### "No genres/timespans found"

Run discovery first:

```bash
python audiobook_catalog_crawler.py
```

This creates `catalog_cache/genres.json` and `timespans.json`.

### Scheduled Task Not Running

1. **Check Task Scheduler:**
   - Open Task Scheduler
   - Find "AudiobookWeeklyBatch"
   - Check "Last Run Result" (should be 0x0 for success)

2. **Test manually:**
   ```bash
   schtasks /Run /TN "AudiobookWeeklyBatch"
   ```

3. **Check logs:**
   - Open `audiobook_auto.log`
   - Look for errors

4. **Common issues:**
   - qBittorrent not running when task executes
   - Network not available at scheduled time
   - Python venv not activated

### qBittorrent Connection Failed

Make sure:
- qBittorrent is running
- Web UI is enabled
- Credentials in `.env` are correct
- Port 52095 is accessible

Test with:
```bash
python test_qb_connection.py
```

### Too Many/Too Few Results

Adjust `top_n_per_genre` in config:

```json
{
  "query_settings": {
    "top_n_per_genre": 20  // More results
  }
}
```

Or:

```json
{
  "query_settings": {
    "top_n_per_genre": 5   // Fewer results
  }
}
```

## 📅 Workflow Examples

### Weekly Discovery (Recommended)

**Monday 2am:**
1. Task runs automatically
2. Queries all genres
3. Grabs top 10 from each
4. Adds to qBittorrent
5. Generates report
6. You wake up to new audiobooks! ☕

### Monthly Deep Dive

Run with higher top_n monthly:

```bash
# Edit config temporarily
# Set "top_n_per_genre": 50

python audiobook_auto_batch.py

# Revert config back to 10 for weekly runs
```

### Test New Genres

1. Remove a genre from `excluded_genres`
2. Run dry-run to see what you'd get:
   ```bash
   python audiobook_auto_batch.py --dry-run
   ```
3. If good, run for real:
   ```bash
   python audiobook_auto_batch.py
   ```

## 🔄 Update Workflow

When the website adds new genres or changes structure:

1. **Re-run discovery:**
   ```bash
   python audiobook_catalog_crawler.py
   ```

2. **Check new genres:**
   ```bash
   python audiobook_query.py genres
   ```

3. **Update excluded list** if needed

4. **Test batch:**
   ```bash
   python audiobook_auto_batch.py --dry-run
   ```

## 📈 Expected Results

### Typical Weekly Run

With default settings (top 10 per genre, ~15-20 active genres):

- **Genres Processed:** 15-20
- **Audiobooks Found:** 150-200
- **Audiobooks Added:** 120-150 (some may have no download links)
- **Duration:** 30-60 minutes
- **qBittorrent Torrents:** +120-150 new downloads

### Disk Space

Audiobooks average 200-500MB each:
- 150 audiobooks × 300MB = **~45GB per week**
- Monthly: **~180GB**

Make sure you have adequate storage!

## 🚨 Important Notes

### Rate Limiting

The batch processor includes delays between queries:
- 1 second between audiobooks
- 5 seconds between genres

This is respectful to the website. **Do not modify these delays.**

### Duplicate Detection

Currently, the system doesn't detect duplicates. You may download the same audiobook if:
- It appears in multiple genres
- You run the batch multiple times per week

Future enhancement: Track downloaded torrents and skip duplicates.

### Network Dependency

The task requires:
- Internet connection
- Access to the audiobook catalog website
- qBittorrent running

If any are unavailable, the task will log errors and retry next week.

## 🎛️ Task Scheduler Management

### View Task

```powershell
Get-ScheduledTask -TaskName "AudiobookWeeklyBatch"
```

### Manually Run Now

```powershell
schtasks /Run /TN "AudiobookWeeklyBatch"
```

### Disable Task

```powershell
Disable-ScheduledTask -TaskName "AudiobookWeeklyBatch"
```

### Enable Task

```powershell
Enable-ScheduledTask -TaskName "AudiobookWeeklyBatch"
```

### Remove Task

```powershell
Unregister-ScheduledTask -TaskName "AudiobookWeeklyBatch" -Confirm:$false
```

## 🔮 Future Enhancements

Planned features:

- [ ] Duplicate detection (skip already downloaded)
- [ ] Seeder count filtering (min seeders)
- [ ] Size filtering (min/max file size)
- [ ] Rating/popularity sorting
- [ ] Email notifications
- [ ] Web dashboard for results
- [ ] Integration with Plex/Audiobookshelf
- [ ] Smart genre rotation (different genres each week)

## 💡 Tips & Tricks

### Weekly Variety

Change `top_n_per_genre` weekly for variety:
- Week 1: Top 5 from ALL genres
- Week 2: Top 20 from 3 favorite genres
- Week 3: Top 10 from unexplored genres

### Genre Rotation

Create multiple config files:

**audiobook_config_scifi.json** - SciFi only
**audiobook_config_mystery.json** - Mystery only

Run different configs on different schedules:
```bash
python audiobook_auto_batch.py --config audiobook_config_scifi.json
```

### Quality Over Quantity

Lower `top_n_per_genre` to 3-5 for curated selection instead of bulk downloading.

### Storage Management

Set qBittorrent to:
- Auto-pause after seeding ratio is met
- Auto-delete torrents after X days
- Move completed to specific folder for organization

## 📞 Support

Check logs for errors:
- `audiobook_auto.log` - Main log
- `batch_report_*.txt` - Summary reports
- Task Scheduler History - Windows task execution logs

Common issues and solutions are in the Troubleshooting section above.

---

**Happy automated audiobook hunting!** 📚🤖
