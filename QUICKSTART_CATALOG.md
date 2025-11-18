# Audiobook Catalog Crawler - Quick Start Guide

## 🚀 Run in 3 Steps

### Step 1: Open Terminal

```bash
cd c:\Users\dogma\Projects\MAMcrawler
```

### Step 2: Run Docker Test

```bash
# Windows (double-click or run in CMD)
run_docker_catalog_test.bat

# Or manually:
docker-compose -f docker-compose.catalog.yml build
docker-compose -f docker-compose.catalog.yml up
```

### Step 3: View Results

```bash
# View the latest markdown report
dir /O-D catalog_test_results\test_report_*.md

# Or JSON
dir /O-D catalog_test_results\test_results_*.json

# Or CSV (open in Excel)
dir /O-D catalog_test_results\audiobooks_*.csv
```

## 📋 What Just Happened?

The system:
1. ✅ Built a Docker container with Chromium browser
2. ✅ Crawled https://mango-mushroom-0d3dde80f.azurestaticapps.net/
3. ✅ Extracted genres: Science Fiction, Fantasy
4. ✅ Queried top 10 audiobooks for each genre
5. ✅ Generated reports in JSON, CSV, and Markdown formats

## 🎯 Next: Customize It

### Add More Genres

Edit `audiobook_catalog_config.json`:

```json
{
  "whitelisted_genres": [
    {"name": "Science Fiction", "value": "13", "enabled": true},
    {"name": "Fantasy", "value": "14", "enabled": true},
    {"name": "Mystery", "value": "15", "enabled": true}  ← Add this
  ]
}
```

### Change Timespan (Weekly → Monthly)

```json
{
  "timespan_preference": {
    "value": "4",                  ← Change from "3" to "4"
    "label": "Last 30 days"        ← Update label
  }
}
```

### Get Top 20 Instead of Top 10

```json
{
  "extraction_settings": {
    "max_results_per_genre": 20   ← Change from 10 to 20
  }
}
```

## 🔁 Run Again

```bash
docker-compose -f docker-compose.catalog.yml up
```

Docker remembers the build, so subsequent runs are **much faster** (30-60 seconds).

## 📁 Output Files Explained

### `test_results_*.json` - Complete Data
- All audiobooks found
- Timestamps and duration
- Validation results
- Error logs (if any)

### `audiobooks_*.csv` - Spreadsheet Format
- Open in Excel/Google Sheets
- Filter by genre
- Sort by rank
- Perfect for sharing

### `test_report_*.md` - Human-Readable
- Executive summary
- Statistics
- Full audiobook list per genre
- Screenshots references

## 🐛 Troubleshooting

### "Docker not found"

Install Docker Desktop:
- **Windows**: https://docs.docker.com/desktop/install/windows-install/
- **Mac**: https://docs.docker.com/desktop/install/mac-install/
- **Linux**: https://docs.docker.com/engine/install/

### "Build taking forever"

**First build** takes 5-10 minutes (installs Chromium). Subsequent builds are cached and take < 30 seconds.

### "No audiobooks found"

1. Check screenshot: `catalog_cache\results_*.png`
2. Check raw HTML: `catalog_cache\raw_results.html`
3. Website structure may have changed
4. Report issue with screenshot

### "Encoding errors" (Windows)

Use Docker - it handles encoding automatically. Or set:
```bash
set PYTHONIOENCODING=utf-8
```

## 📚 Full Documentation

- **Complete Guide**: [CATALOG_SYSTEM_SUMMARY.md](CATALOG_SYSTEM_SUMMARY.md)
- **Docker Details**: [DOCKER_CATALOG_README.md](DOCKER_CATALOG_README.md)
- **Original README**: [AUDIOBOOK_CATALOG_README.md](AUDIOBOOK_CATALOG_README.md)

## 🎉 Success Looks Like

```
======================================================================
📊 TEST SUMMARY
======================================================================
Validation Status: ✅ PASSED
Duration: 45.23 seconds
Genres Tested: 2
Successful: 2
Failed: 0
Total Audiobooks: 20
======================================================================
```

Your results are in `catalog_test_results/`

Enjoy your automated audiobook discoveries! 🚀📚
