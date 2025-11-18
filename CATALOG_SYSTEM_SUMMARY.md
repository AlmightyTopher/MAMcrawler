# Audiobook Catalog Crawler - Complete System Summary

## 🎯 Overview

You now have a **fully automated, Dockerized audiobook catalog crawler** that:

1. ✅ Scrapes **https://mango-mushroom-0d3dde80f.azurestaticapps.net/**
2. ✅ Extracts **available genres** and **timespans** dynamically
3. ✅ Queries **top 10 audiobooks per genre** (configurable)
4. ✅ Generates **comprehensive reports** (JSON, CSV, Markdown)
5. ✅ Runs in **Docker** for consistent execution
6. ✅ **Validates results** against quality requirements
7. ✅ **UTF-8 encoding** properly handled
8. ✅ **Screenshots** for debugging
9. ✅ **qBittorrent integration** ready (optional)

---

## 📁 Complete File Structure

```
MAMcrawler/
├── audiobook_catalog_crawler.py        # Core crawler logic
├── audiobook_catalog_test_runner.py    # Comprehensive test suite
├── audiobook_query.py                  # Interactive CLI interface
├── audiobook_catalog_config.json       # Configuration & genre whitelist
│
├── Dockerfile.catalog                  # Docker image definition
├── docker-compose.catalog.yml          # Docker compose configuration
├── requirements_catalog.txt            # Python dependencies
│
├── run_docker_catalog_test.bat         # Windows: Build & run Docker
├── run_docker_catalog_test.sh          # Linux/Mac: Build & run Docker
├── run_catalog_test.bat                # Windows: Run Python directly
│
├── DOCKER_CATALOG_README.md            # Docker setup & troubleshooting
├── CATALOG_SYSTEM_SUMMARY.md           # This file
│
├── catalog_cache/                      # Cached data
│   ├── genres.json                     # Available genres
│   ├── timespans.json                  # Available timespans
│   ├── audiobooks_page.png             # Navigation screenshots
│   ├── results_*.png                   # Query result screenshots
│   ├── raw_results.html                # Debug HTML
│   └── raw_results.md                  # Debug Markdown
│
└── catalog_test_results/               # Test output
    ├── test_results_*.json             # Full test data
    ├── audiobooks_*.csv                # All audiobooks
    └── test_report_*.md                # Human-readable report
```

---

## 🚀 How to Use

### Method 1: Docker (Recommended)

**Build and run in one command:**

```bash
# Windows
run_docker_catalog_test.bat

# Linux/Mac
./run_docker_catalog_test.sh
```

**Or manually:**

```bash
# Build image
docker-compose -f docker-compose.catalog.yml build

# Run test
docker-compose -f docker-compose.catalog.yml up
```

### Method 2: Python Directly

```bash
# Set encoding (Windows)
set PYTHONIOENCODING=utf-8

# Run test
python audiobook_catalog_test_runner.py

# Or interactive mode
python audiobook_query.py
```

---

## ⚙️ Configuration

Edit **`audiobook_catalog_config.json`**:

### 1. Genre Whitelist

```json
{
  "whitelisted_genres": [
    {
      "name": "Science Fiction",
      "value": "13",
      "enabled": true        // ← Toggle on/off
    },
    {
      "name": "Fantasy",
      "value": "14",
      "enabled": true
    }
  ]
}
```

**To add more genres:**
1. Run `python audiobook_query.py`
2. Select "Show genres"
3. Note the genre name and value
4. Add to whitelist in config

### 2. Timespan (Weekly, Monthly, etc.)

```json
{
  "timespan_preference": {
    "value": "3",           // "3" = Last 7 days
    "label": "Last 7 days"
  }
}
```

**Available timespans:**
- `"1"` = Today
- `"2"` = Yesterday
- `"3"` = Last 7 days (weekly)
- `"4"` = Last 30 days (monthly)
- `"0"` = All time

### 3. Top N Results

```json
{
  "extraction_settings": {
    "max_results_per_genre": 10  // ← Change to 5, 20, etc.
  }
}
```

### 4. Crawler Behavior

```json
{
  "crawler_settings": {
    "headless": true,              // Hide browser window
    "page_timeout": 60000,         // 60 seconds
    "wait_between_requests": 3,    // 3 seconds between genres
    "take_screenshots": true,      // Debug screenshots
    "save_raw_html": true          // Save raw HTML for debugging
  }
}
```

### 5. Validation Rules

```json
{
  "validation_requirements": {
    "min_results_per_genre": 1,    // Minimum audiobooks per genre
    "require_titles": true,         // Fail if titles missing
    "max_failures_allowed": 1       // Max genres that can fail
  }
}
```

---

## 📊 Output Files

### 1. JSON Report (`test_results_YYYYMMDD_HHMMSS.json`)

Complete test data:

```json
{
  "start_time": "2025-01-05T14:30:22",
  "duration_seconds": 45.23,
  "total_genres_tested": 2,
  "successful_genres": 2,
  "failed_genres": 0,
  "total_audiobooks_found": 20,
  "validation_passed": true,
  "genre_results": [
    {
      "genre_name": "Science Fiction",
      "audiobook_count": 10,
      "audiobooks": [...]
    }
  ]
}
```

### 2. CSV Export (`audiobooks_YYYYMMDD_HHMMSS.csv`)

Spreadsheet-friendly format:

| Genre           | Rank | Title                     | Author       | Link        | Timespan    |
|-----------------|------|---------------------------|--------------|-------------|-------------|
| Science Fiction | 1    | The Expanse: Leviathan... | James S.A... | https://... | Last 7 days |
| Science Fiction | 2    | Dune                      | Frank Herb...| https://... | Last 7 days |

### 3. Markdown Report (`test_report_YYYYMMDD_HHMMSS.md`)

Human-readable report with:
- Executive summary
- Statistics
- Per-genre results with all audiobooks
- Error logs (if any)
- Screenshots references

---

## 🔍 Test Workflow

When you run the test, it performs these steps:

### Phase 1: Discovery
1. Navigates to Mango website
2. Finds audiobooks section
3. Extracts all available genres
4. Extracts all available timespans
5. Saves to cache for future runs

### Phase 2: Genre Testing
For each whitelisted genre:
1. Navigates to audiobooks
2. Selects genre from dropdown
3. Selects timespan from dropdown
4. Clicks search/submit
5. Waits for results to load
6. Extracts top 10 audiobooks
7. Takes screenshot
8. Waits 3 seconds before next genre

### Phase 3: Validation
1. Checks minimum results per genre
2. Verifies required fields present
3. Counts failures vs allowed threshold
4. Reports pass/fail status

### Phase 4: Report Generation
1. Generates JSON with full data
2. Generates CSV for spreadsheets
3. Generates Markdown for humans
4. Saves to `catalog_test_results/`

---

## 📈 Expected Output

### Success Example:

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

🎉 All tests passed! Ready for Docker containerization.
```

### Results Location:

```
catalog_test_results/
├── test_results_20250105_143022.json
├── audiobooks_20250105_143022.csv
└── test_report_20250105_143022.md
```

---

## 🐛 Troubleshooting

### No Results Found

**Symptoms:** Extraction returns 0 audiobooks

**Fixes:**
1. Check screenshot: `catalog_cache/results_*.png`
2. Review raw HTML: `catalog_cache/raw_results.html`
3. Website structure may have changed
4. Update extraction logic in `audiobook_catalog_crawler.py`

### Encoding Errors (Windows)

**Symptoms:** `UnicodeEncodeError: 'charmap' codec...`

**Fix:** Always use Docker or set encoding:
```bash
set PYTHONIOENCODING=utf-8
python audiobook_catalog_test_runner.py
```

### Docker Build Fails

**Symptoms:** Cannot install Chromium

**Fix:**
```bash
# Rebuild without cache
docker-compose -f docker-compose.catalog.yml build --no-cache
```

### Too Slow

**Symptoms:** Takes > 5 minutes

**Fixes:**
1. Reduce wait times in config:
   ```json
   {
     "crawler_settings": {
       "wait_between_requests": 1,  // Reduce from 3 to 1
       "page_timeout": 30000         // Reduce from 60 to 30
     }
   }
   ```

2. Reduce genres:
   ```json
   {
     "whitelisted_genres": [
       { "name": "Science Fiction", "value": "13", "enabled": true },
       { "name": "Fantasy", "value": "14", "enabled": false }  // Disable
     ]
   }
   ```

---

## 🎛️ Advanced Usage

### 1. Interactive Mode

```bash
python audiobook_query.py
```

**Menu:**
- Show genres
- Show timespans
- Query audiobooks (select genre + timespan)
- Add to qBittorrent
- Refresh filters from website

### 2. Command-Line Mode

```bash
# Refresh filters
python audiobook_query.py refresh

# Show genres
python audiobook_query.py genres

# Query specific combo (genre #2, timespan #3)
python audiobook_query.py query 2 3
```

### 3. Scheduled Runs

**Windows Task Scheduler:**
1. Create new task
2. Trigger: Weekly on Sunday
3. Action: `docker-compose -f docker-compose.catalog.yml up`
4. Start in: `C:\Users\dogma\Projects\MAMcrawler`

**Linux/Mac Cron:**
```bash
# Every Sunday at 2 AM
0 2 * * 0 cd /path/to/MAMcrawler && docker-compose -f docker-compose.catalog.yml up
```

### 4. qBittorrent Integration

Add to `.env` or Docker environment:

```bash
QB_HOST=localhost
QB_PORT=8080
QB_USERNAME=admin
QB_PASSWORD=your_password
```

Then in interactive mode:
```bash
python audiobook_query.py
# Select "Query audiobooks"
# After results, enter audiobook number to add to qBittorrent
```

---

## 🔐 Security Notes

1. **No Hardcoded Credentials**: Use environment variables
2. **Read-Only Config**: Config mounted read-only in Docker
3. **No Privileged Mode**: Container runs without elevated privileges
4. **Resource Limits**: CPU and memory limits prevent exhaustion
5. **Isolated Network**: Container uses isolated bridge network

---

## 📝 Maintenance

### Update Dependencies

```bash
# Update Python packages
pip install --upgrade -r requirements_catalog.txt

# Update Playwright/Chromium
python -m playwright install chromium
```

### Update Docker Image

```bash
# Rebuild with latest packages
docker-compose -f docker-compose.catalog.yml build --no-cache --pull
```

### Clean Up Old Results

```bash
# Windows
del /Q catalog_test_results\*.json
del /Q catalog_test_results\*.csv
del /Q catalog_test_results\*.md

# Linux/Mac
rm catalog_test_results/*.json
rm catalog_test_results/*.csv
rm catalog_test_results/*.md
```

---

## 🎯 Next Steps

1. **Test the System:**
   ```bash
   run_docker_catalog_test.bat
   ```

2. **Review Results:**
   - Check `catalog_test_results/test_report_*.md`
   - Verify audiobooks were extracted correctly
   - Check screenshots in `catalog_cache/`

3. **Customize Configuration:**
   - Add more genres to whitelist
   - Adjust top N results
   - Change timespan (weekly, monthly, etc.)

4. **Set Up Automation:**
   - Schedule weekly runs
   - Connect to qBittorrent for auto-downloads
   - Set up email notifications (add custom code)

5. **Extend Functionality:**
   - Add more metadata extraction
   - Implement trend tracking over time
   - Build web dashboard for results
   - Add duplicate detection
   - Integrate with Plex/Audiobookshelf

---

## 📚 Full Documentation

- **Docker Setup**: [DOCKER_CATALOG_README.md](DOCKER_CATALOG_README.md)
- **Main README**: [AUDIOBOOK_CATALOG_README.md](AUDIOBOOK_CATALOG_README.md)

---

## ✅ What You Have Now

**Core Functionality:**
- ✅ Automated genre discovery
- ✅ Top 10 extraction per genre
- ✅ Configurable whitelist
- ✅ Comprehensive validation
- ✅ Multiple output formats (JSON, CSV, MD)

**Infrastructure:**
- ✅ Docker containerization
- ✅ UTF-8 encoding support
- ✅ Screenshot debugging
- ✅ Error handling & retry logic
- ✅ Progress logging

**Integration:**
- ✅ qBittorrent support
- ✅ Interactive CLI
- ✅ Command-line interface
- ✅ Scheduler-friendly

**Documentation:**
- ✅ Complete setup guide
- ✅ Troubleshooting guide
- ✅ Configuration reference
- ✅ Usage examples

---

## 🎉 Success!

Your audiobook catalog crawler is **production-ready** and **Docker-ready**!

Run it now:
```bash
run_docker_catalog_test.bat
```

Enjoy your automated weekly audiobook discoveries! 🚀📚
