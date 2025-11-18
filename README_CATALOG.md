# 🎵 Audiobook Catalog Crawler

Automated Docker-based crawler for **https://mango-mushroom-0d3dde80f.azurestaticapps.net/** that extracts top weekly audiobooks by genre.

---

## ⚡ Quick Start

### Production Mode (Run Tests)
```bash
run_docker_catalog_test.bat
```

### Development Mode (Edit & Test)
```bash
dev_start.bat
code .
# Edit files, then:
dev_run_test.bat
```

---

## 📊 What It Does

1. ✅ Crawls Mango audiobook catalog
2. ✅ Discovers genres & timespans dynamically
3. ✅ Queries top 10 audiobooks per genre
4. ✅ Generates JSON, CSV, and Markdown reports
5. ✅ Takes screenshots for debugging
6. ✅ Validates results quality

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| **Production** | |
| `run_docker_catalog_test.bat` | Build & run tests |
| `docker-compose.catalog.yml` | Production config |
| **Development** | |
| `dev_start.bat` | Start dev container |
| `dev_run_test.bat` | Run tests |
| `dev_shell.bat` | Open bash |
| `docker-compose.catalog.dev.yml` | Dev config |
| **Code** | |
| `audiobook_catalog_crawler.py` | Core crawler |
| `audiobook_catalog_test_runner.py` | Test suite |
| `audiobook_catalog_config.json` | Configuration |
| `audiobook_query.py` | Interactive CLI |

---

## ⚙️ Configuration

Edit **`audiobook_catalog_config.json`**:

```json
{
  "whitelisted_genres": [
    {"name": "Science Fiction", "value": "13", "enabled": true},
    {"name": "Fantasy", "value": "14", "enabled": true}
  ],
  "timespan_preference": {
    "value": "3",
    "label": "Last 7 days"
  },
  "extraction_settings": {
    "max_results_per_genre": 10
  }
}
```

---

## 📈 Output

Results saved to **`catalog_test_results/`**:

- **JSON** (`test_results_*.json`) - Complete data
- **CSV** (`audiobooks_*.csv`) - Spreadsheet format
- **Markdown** (`test_report_*.md`) - Human-readable

---

## 🔧 Development Workflow

```bash
# 1. Start container (once)
dev_start.bat

# 2. Edit files in VS Code
code .

# 3. Test changes
dev_run_test.bat

# 4. Repeat 2-3 as needed

# 5. Stop when done
dev_stop.bat
```

**Changes sync instantly - no rebuilds!**

---

## 📚 Documentation

| Guide | Purpose |
|-------|---------|
| [**DEV_CHEATSHEET.md**](DEV_CHEATSHEET.md) | Quick command reference |
| [**QUICKSTART_CATALOG.md**](QUICKSTART_CATALOG.md) | 3-step getting started |
| [**DEVELOPER_GUIDE.md**](DEVELOPER_GUIDE.md) | Complete dev workflow |
| [**CATALOG_SYSTEM_SUMMARY.md**](CATALOG_SYSTEM_SUMMARY.md) | Full system overview |
| [**DOCKER_CATALOG_README.md**](DOCKER_CATALOG_README.md) | Docker troubleshooting |

---

## 🎯 Use Cases

### Weekly Audiobook Discovery
```bash
# Run every Sunday
run_docker_catalog_test.bat
# Check catalog_test_results/audiobooks_*.csv
```

### Track Trends Over Time
```bash
# Run weekly, compare CSVs
# See which audiobooks trend up
```

### Auto-Download (qBittorrent)
```bash
# Configure QB settings
# Use audiobook_query.py interactively
python audiobook_query.py
# Select audiobook → adds to qBittorrent
```

---

## 🚀 Features

- ✅ **Dockerized** - Consistent environment
- ✅ **Live Code Sync** - Edit on host, runs in Docker
- ✅ **UTF-8 Support** - Handles special characters
- ✅ **Screenshot Debug** - Visual confirmation
- ✅ **Validation** - Quality checks
- ✅ **Multiple Formats** - JSON, CSV, Markdown
- ✅ **qBittorrent Ready** - Auto-download integration

---

## 💡 Tips

- **First run**: Takes 5-10 minutes (installs Chromium)
- **Subsequent runs**: 30-60 seconds
- **Best timespan**: "Last 7 days" for weekly top 10
- **Check screenshots**: If extraction fails, review `catalog_cache/*.png`
- **Use dev mode**: For iterative development

---

## 🐛 Troubleshooting

### No Results
1. Check `catalog_cache/results_*.png`
2. Review `catalog_cache/raw_results.html`
3. Website structure may have changed

### Docker Issues
```bash
# Rebuild from scratch
docker-compose -f docker-compose.catalog.yml build --no-cache
```

### Encoding Errors (Windows)
Use Docker - it handles encoding automatically.

---

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

---

## 📞 Support

- **Docs**: See guides above
- **Logs**: `audiobook_catalog_test.log`
- **Screenshots**: `catalog_cache/*.png`
- **Raw HTML**: `catalog_cache/raw_results.html`

---

## 🚀 Get Started Now

**Production (run tests):**
```bash
run_docker_catalog_test.bat
```

**Development (edit code):**
```bash
dev_start.bat
code .
```

Enjoy your automated audiobook discoveries! 📚
