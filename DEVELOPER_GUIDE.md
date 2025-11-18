# Audiobook Catalog Crawler - Developer Guide

## 🎯 Development Mode Overview

You can now edit the code in **VS Code on your machine** and it **automatically syncs to Docker**. No rebuilding needed!

---

## 🚀 Quick Start (Development Mode)

### Step 1: Start Development Container

```bash
dev_start.bat
```

This starts a Docker container with:
- ✅ Live code sync (edit on host → runs in Docker)
- ✅ All dependencies installed
- ✅ Chromium browser ready
- ✅ UTF-8 encoding configured
- ✅ Persistent storage for results

### Step 2: Open in VS Code

```bash
code .
```

Or:
1. Open VS Code
2. File → Open Folder
3. Select `C:\Users\dogma\Projects\MAMcrawler`

### Step 3: Edit & Test

**Edit any file:**
- `audiobook_catalog_crawler.py`
- `audiobook_catalog_test_runner.py`
- `audiobook_catalog_config.json`
- `audiobook_query.py`

**Run tests immediately:**
```bash
dev_run_test.bat
```

Changes apply **instantly** - no rebuild required!

---

## 📂 Development Files

| File | Purpose |
|------|---------|
| `docker-compose.catalog.dev.yml` | Development container config |
| `dev_start.bat` | Start dev container |
| `dev_stop.bat` | Stop dev container |
| `dev_run_test.bat` | Run tests in container |
| `dev_shell.bat` | Open bash shell |
| `dev_python.bat` | Open Python REPL |

---

## 🔧 Development Commands

### Start Container
```bash
dev_start.bat
```
Starts container in background, keeps running.

### Run Test Suite
```bash
dev_run_test.bat
```
Executes `audiobook_catalog_test_runner.py` inside container.

### Open Bash Shell
```bash
dev_shell.bat
```
Opens interactive bash terminal inside container.

**Use for:**
- Running ad-hoc Python commands
- Debugging issues
- Installing packages temporarily
- Exploring file system

### Open Python REPL
```bash
dev_python.bat
```
Opens Python interpreter inside container.

**Use for:**
- Testing code snippets
- Importing and testing modules
- Interactive debugging

### Stop Container
```bash
dev_stop.bat
```
Stops and removes container (keeps volumes).

---

## 💡 Typical Development Workflow

### Scenario 1: Change Configuration

**Want to add a new genre?**

1. **Edit config** in VS Code:
   ```json
   // audiobook_catalog_config.json
   {
     "whitelisted_genres": [
       {"name": "Science Fiction", "value": "13", "enabled": true},
       {"name": "Fantasy", "value": "14", "enabled": true},
       {"name": "Mystery", "value": "15", "enabled": true}  // ← Add
     ]
   }
   ```

2. **Save file** (Ctrl+S)

3. **Run test**:
   ```bash
   dev_run_test.bat
   ```

4. **Check results**:
   ```bash
   catalog_test_results\test_report_*.md
   ```

No Docker rebuild needed! 🎉

---

### Scenario 2: Fix Extraction Logic

**Website changed and extraction broke?**

1. **Start dev container** (if not running):
   ```bash
   dev_start.bat
   ```

2. **Open crawler** in VS Code:
   ```python
   # audiobook_catalog_crawler.py

   async def _extract_audiobooks_from_html(self, html: str, markdown: str):
       # Edit extraction logic here
       for row in soup.find_all('tr', class_='new-class'):  # ← Change selector
           ...
   ```

3. **Save file** (Ctrl+S)

4. **Test immediately**:
   ```bash
   dev_run_test.bat
   ```

5. **Check screenshots** to verify:
   ```bash
   catalog_cache\results_*.png
   ```

6. **Iterate** until it works!

---

### Scenario 3: Debug Interactively

**Need to test something quickly?**

1. **Open shell**:
   ```bash
   dev_shell.bat
   ```

2. **Run Python interactively**:
   ```bash
   python
   ```

3. **Import and test**:
   ```python
   from audiobook_catalog_crawler import AudiobookCatalogCrawler

   crawler = AudiobookCrawler()
   # Test methods here
   ```

4. **Exit** when done:
   ```python
   exit()
   ```

---

### Scenario 4: Add New Feature

**Want to add email notifications?**

1. **Edit test runner** in VS Code:
   ```python
   # audiobook_catalog_test_runner.py

   async def _generate_reports(self):
       # ... existing code ...

       # Add email notification
       self._send_email_notification()

   def _send_email_notification(self):
       import smtplib
       # Your email logic here
   ```

2. **Save file**

3. **Test**:
   ```bash
   dev_run_test.bat
   ```

4. **Debug** if needed:
   ```bash
   dev_shell.bat
   python audiobook_catalog_test_runner.py
   ```

---

## 🔍 VS Code Integration

### Recommended Extensions

1. **Python** (ms-python.python)
   - Syntax highlighting
   - IntelliSense
   - Debugging

2. **Docker** (ms-azuretools.vscode-docker)
   - View running containers
   - Attach to container
   - View logs

3. **Remote - Containers** (ms-vscode-remote.remote-containers)
   - Develop inside container
   - Full VS Code experience

### Attach VS Code to Container

**Option 1: Docker Extension**
1. Install Docker extension
2. View → Docker
3. Right-click `audiobook-catalog-dev`
4. Select "Attach Visual Studio Code"

**Option 2: Remote Containers**
1. Install Remote-Containers extension
2. F1 → "Remote-Containers: Attach to Running Container"
3. Select `audiobook-catalog-dev`
4. Edit files inside container directly

---

## 📝 Live Code Sync Details

### What's Synced?

These files sync **bi-directionally** (host ↔ container):

```
audiobook_catalog_crawler.py       ← Core crawler
audiobook_catalog_test_runner.py   ← Test suite
audiobook_query.py                 ← CLI tool
audiobook_catalog_config.json      ← Configuration
catalog_cache/                     ← Screenshots & data
catalog_test_results/              ← Output reports
*.log                              ← Log files
```

### How It Works

Docker **volume mounts** map host files to container:

```yaml
volumes:
  - ./audiobook_catalog_crawler.py:/app/audiobook_catalog_crawler.py:rw
```

**When you save a file in VS Code:**
1. File writes to host filesystem
2. Docker detects change via volume mount
3. Container sees updated file instantly
4. Next run uses new code

**No rebuild needed!**

---

## 🧪 Testing Strategies

### Unit Testing (Quick)

Test specific functions:

```bash
dev_shell.bat
```

```python
python
>>> from audiobook_catalog_crawler import AudiobookCatalogCrawler
>>> crawler = AudiobookCatalogCrawler()
>>> result = crawler._anonymize_data("test@email.com")
>>> print(result)
'[EMAIL]'
```

### Integration Testing (Full)

Test entire workflow:

```bash
dev_run_test.bat
```

Reviews:
- Discovery phase
- Genre querying
- Validation
- Report generation

### Screenshot Debugging

Check visual results:

```bash
# View screenshots
explorer catalog_cache\
```

Look at:
- `audiobooks_page.png` - Navigation
- `results_13_3.png` - Sci-fi results
- `results_14_3.png` - Fantasy results

---

## 🛠️ Advanced Usage

### Install Additional Packages

```bash
dev_shell.bat
```

```bash
pip install some-package
```

**Note:** Temporary! Lost on container restart.

**To persist:**
1. Edit `requirements_catalog.txt`
2. Rebuild:
   ```bash
   docker-compose -f docker-compose.catalog.dev.yml build
   ```

### Run Specific Script

```bash
dev_shell.bat
```

```bash
python audiobook_query.py
python -m pytest tests/
```

### View Logs

**Real-time:**
```bash
docker-compose -f docker-compose.catalog.dev.yml logs -f audiobook-catalog-dev
```

**On host:**
```bash
type audiobook_catalog_test.log
```

### Custom Python Command

```bash
dev_shell.bat
```

```bash
python -c "from audiobook_catalog_crawler import *; print('Hello')"
```

---

## 🚨 Common Issues

### Container Won't Start

**Check if already running:**
```bash
docker ps -a | findstr audiobook
```

**Stop and restart:**
```bash
dev_stop.bat
dev_start.bat
```

### Changes Not Applying

**Verify volume mounts:**
```bash
docker-compose -f docker-compose.catalog.dev.yml config
```

**Restart container:**
```bash
dev_stop.bat
dev_start.bat
```

### Permission Errors

**Windows:**
- Ensure Docker Desktop has access to your drive
- Docker Desktop → Settings → Resources → File Sharing

### Container Exits Immediately

**Check logs:**
```bash
docker-compose -f docker-compose.catalog.dev.yml logs
```

**Start with shell:**
```bash
docker-compose -f docker-compose.catalog.dev.yml run --rm audiobook-catalog-dev bash
```

---

## 📊 Comparison: Dev vs Production

| Feature | Development (`dev_start.bat`) | Production (`run_docker_catalog_test.bat`) |
|---------|-------------------------------|-------------------------------------------|
| **Purpose** | Edit & test code | Run automated tests |
| **Container** | Stays running | Runs once, exits |
| **Code sync** | ✅ Live (edit in VS Code) | ❌ Baked into image |
| **Rebuilds** | ❌ Not needed | ✅ Needed for code changes |
| **Use case** | Development, debugging | Scheduled runs, CI/CD |
| **Speed** | ⚡ Instant changes | 🐌 Rebuild for changes |

---

## 🎓 Learning Resources

### Docker Basics

- **Volumes**: https://docs.docker.com/storage/volumes/
- **Compose**: https://docs.docker.com/compose/

### Python Development

- **VS Code Python**: https://code.visualstudio.com/docs/languages/python
- **Debugging**: https://code.visualstudio.com/docs/python/debugging

### Crawl4AI

- **Docs**: https://crawl4ai.com/
- **GitHub**: https://github.com/unclecode/crawl4ai

---

## 🎯 Next Steps

1. **Start dev container:**
   ```bash
   dev_start.bat
   ```

2. **Open in VS Code:**
   ```bash
   code .
   ```

3. **Make a small change** to test workflow:
   ```json
   // audiobook_catalog_config.json
   {
     "extraction_settings": {
       "max_results_per_genre": 5  // Change from 10 to 5
     }
   }
   ```

4. **Run test:**
   ```bash
   dev_run_test.bat
   ```

5. **Verify** results show only 5 audiobooks per genre

6. **Iterate!** Keep editing and testing.

---

## 🎉 You're Ready!

You now have a **live development environment** where:
- ✅ Edit code in VS Code
- ✅ Changes apply instantly in Docker
- ✅ Test immediately without rebuilds
- ✅ Debug interactively
- ✅ All dependencies handled

Happy coding! 🚀
