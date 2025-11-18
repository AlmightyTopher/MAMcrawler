# Audiobook Catalog Crawler - Docker Setup

Complete Docker containerization for automated audiobook catalog crawling and testing.

## 📦 What's Included

- **Dockerized Crawler**: Full Chromium browser environment for JavaScript-based sites
- **Automated Testing**: Runs comprehensive tests across all whitelisted genres
- **Top 10 Extraction**: Automatically extracts top 10 audiobooks per genre
- **Report Generation**: Creates JSON, CSV, and Markdown reports
- **Volume Persistence**: Results saved to host machine
- **UTF-8 Support**: Handles Unicode characters properly in Docker

## 🚀 Quick Start

### Prerequisites

- Docker Desktop installed and running
- Docker Compose V2
- At least 2GB free RAM
- 2GB free disk space

### Step 1: Build the Container

```bash
# Build the Docker image
docker-compose -f docker-compose.catalog.yml build
```

This will:
- Install Python 3.11
- Install Chromium browser with Playwright
- Install all Python dependencies
- Set up UTF-8 encoding environment

### Step 2: Run the Test

```bash
# Run the comprehensive test
docker-compose -f docker-compose.catalog.yml up
```

The container will:
1. **Discover** available genres and timespans from the website
2. **Query** each whitelisted genre with the configured timespan
3. **Extract** top 10 audiobooks per genre
4. **Validate** results against requirements
5. **Generate** comprehensive reports
6. **Exit** automatically when complete

### Step 3: View Results

After the test completes, check:

```bash
# View test results
ls catalog_test_results/

# Example files:
# - test_results_20250105_143022.json    (Full test data)
# - audiobooks_20250105_143022.csv       (All audiobooks in CSV)
# - test_report_20250105_143022.md       (Human-readable report)

# View logs
cat audiobook_catalog_test.log

# View screenshots
ls catalog_cache/*.png
```

## 📋 Configuration

### Edit Genre Whitelist

Modify `audiobook_catalog_config.json`:

```json
{
  "whitelisted_genres": [
    {
      "name": "Science Fiction",
      "value": "13",
      "enabled": true
    },
    {
      "name": "Fantasy",
      "value": "14",
      "enabled": true
    },
    {
      "name": "Mystery",
      "value": "15",
      "enabled": false  // Disabled - won't be tested
    }
  ]
}
```

### Change Timespan

Update the timespan preference:

```json
{
  "timespan_preference": {
    "value": "3",
    "label": "Last 7 days"  // Options: Today, Yesterday, Last 7 days, Last 30 days, All time
  }
}
```

### Adjust Top N Results

Change how many audiobooks to extract per genre:

```json
{
  "extraction_settings": {
    "max_results_per_genre": 10  // Change to 5, 20, etc.
  }
}
```

## 🔄 Running Modes

### One-Time Test (Default)

```bash
docker-compose -f docker-compose.catalog.yml up
```

Runs once and exits.

### Scheduled Runs

Use host cron job or Task Scheduler:

**Linux/Mac (crontab):**
```bash
# Run every Sunday at 2 AM
0 2 * * 0 cd /path/to/MAMcrawler && docker-compose -f docker-compose.catalog.yml up
```

**Windows (Task Scheduler):**
1. Create new task
2. Trigger: Weekly on Sunday
3. Action: Start a program
4. Program: `docker-compose`
5. Arguments: `-f docker-compose.catalog.yml up`
6. Start in: `C:\Users\dogma\Projects\MAMcrawler`

### Interactive Development

Run with shell access:

```bash
docker-compose -f docker-compose.catalog.yml run --rm audiobook-catalog-crawler bash

# Inside container:
python audiobook_catalog_test_runner.py
python audiobook_catalog_crawler.py
python audiobook_query.py
```

## 📊 Output Files

### JSON Report (`test_results_*.json`)

Complete test data including:
- All audiobooks found
- Timestamps and duration
- Validation results
- Error logs

```json
{
  "start_time": "2025-01-05T14:30:22",
  "total_genres_tested": 2,
  "successful_genres": 2,
  "total_audiobooks_found": 20,
  "genre_results": [...]
}
```

### CSV Export (`audiobooks_*.csv`)

All audiobooks in spreadsheet format:

```csv
Genre,Rank,Title,Author,Link,Timespan
Science Fiction,1,The Expanse: Leviathan Wakes,James S.A. Corey,https://...,Last 7 days
Science Fiction,2,Dune,Frank Herbert,https://...,Last 7 days
```

### Markdown Report (`test_report_*.md`)

Human-readable report with:
- Executive summary
- Statistics
- Per-genre results
- Error logs

## 🐛 Troubleshooting

### Container Fails to Start

**Issue**: "Cannot find Chromium browser"

**Solution**:
```bash
# Rebuild with --no-cache
docker-compose -f docker-compose.catalog.yml build --no-cache
```

### No Results Found

**Issue**: Extraction returns 0 audiobooks

**Solutions**:
1. Check screenshots in `catalog_cache/*.png`
2. Review raw HTML in `catalog_cache/raw_results.html`
3. Update extraction logic in `audiobook_catalog_crawler.py`
4. Increase wait times in config:
   ```json
   {
     "crawler_settings": {
       "page_timeout": 90000  // 90 seconds
     }
   }
   ```

### Encoding Errors

**Issue**: Unicode characters appear garbled

**Solution**: Already handled in Docker! The container sets:
- `PYTHONIOENCODING=utf-8`
- `LANG=C.UTF-8`
- `LC_ALL=C.UTF-8`

### Out of Memory

**Issue**: Container crashes with OOM error

**Solution**: Increase memory limit in `docker-compose.catalog.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 4G  # Increase from 2G
```

## 🔧 Advanced Configuration

### Connect to qBittorrent

To test download functionality, uncomment in `docker-compose.catalog.yml`:

```yaml
environment:
  - QB_HOST=host.docker.internal  # Docker host machine
  - QB_PORT=8080
  - QB_USERNAME=admin
  - QB_PASSWORD=your_password
```

**Note**: Ensure qBittorrent Web UI is enabled and accessible.

### Custom Browser Settings

Edit `audiobook_catalog_config.json`:

```json
{
  "crawler_settings": {
    "headless": false,  // Show browser window (requires X11 forwarding)
    "viewport_width": 1366,
    "viewport_height": 768,
    "take_screenshots": true
  }
}
```

### Validation Rules

Customize pass/fail criteria:

```json
{
  "validation_requirements": {
    "min_results_per_genre": 5,  // Fail if < 5 results
    "require_titles": true,       // Fail if missing titles
    "max_failures_allowed": 0     // Fail on any error
  }
}
```

## 📈 CI/CD Integration

### GitHub Actions

```yaml
name: Audiobook Catalog Test

on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Catalog Test
        run: |
          docker-compose -f docker-compose.catalog.yml up --abort-on-container-exit
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: catalog_test_results/
```

### GitLab CI

```yaml
audiobook-test:
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker-compose -f docker-compose.catalog.yml up --abort-on-container-exit
  artifacts:
    paths:
      - catalog_test_results/
    expire_in: 1 week
  only:
    - schedules
```

## 🔒 Security Considerations

1. **No Hardcoded Credentials**: Use environment variables or secrets
2. **Read-Only Config**: Config file mounted read-only in container
3. **No Privileged Mode**: Container runs without elevated privileges
4. **Resource Limits**: CPU and memory limits prevent resource exhaustion
5. **Isolated Network**: Container uses isolated bridge network

## 📝 Maintenance

### Update Dependencies

```bash
# Update Python packages
docker-compose -f docker-compose.catalog.yml build --no-cache

# Update Chromium
docker-compose -f docker-compose.catalog.yml run --rm audiobook-catalog-crawler \
  python -m playwright install chromium
```

### Clean Up

```bash
# Remove containers and networks
docker-compose -f docker-compose.catalog.yml down

# Remove volumes (caution: deletes results)
docker-compose -f docker-compose.catalog.yml down -v

# Remove images
docker rmi $(docker images -q -f "reference=*audiobook-catalog*")
```

## 🎯 Success Criteria

The test passes when:
- ✅ All enabled genres are successfully queried
- ✅ At least `min_results_per_genre` audiobooks found per genre
- ✅ All required fields (titles, authors) are present
- ✅ No more than `max_failures_allowed` errors
- ✅ Reports generated successfully

## 📚 Next Steps

After successful Docker testing:

1. **Schedule Regular Runs**: Set up cron or Task Scheduler
2. **Monitor Results**: Track audiobook trends over time
3. **Expand Genres**: Add more genres to whitelist
4. **Integrate Downloads**: Connect to qBittorrent for automation
5. **Build Dashboard**: Create web UI to visualize results

## 💡 Tips

- **First Run**: Takes 2-5 minutes (browser installation)
- **Subsequent Runs**: 30-60 seconds per genre
- **Best Timespan**: "Last 7 days" for weekly top 10
- **Screenshot Debug**: Always check screenshots if extraction fails
- **Log Everything**: Review logs for troubleshooting

## 🆘 Support

If issues persist:

1. Check logs: `audiobook_catalog_test.log`
2. Review screenshots: `catalog_cache/*.png`
3. Inspect raw HTML: `catalog_cache/raw_results.html`
4. Verify website accessibility: Visit https://mango-mushroom-0d3dde80f.azurestaticapps.net/
5. Update extraction selectors in `audiobook_catalog_crawler.py`

## 🎉 Success Example

When everything works:

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

Your results will be in:
- `catalog_test_results/test_results_*.json`
- `catalog_test_results/audiobooks_*.csv`
- `catalog_test_results/test_report_*.md`

Happy crawling! 🚀
