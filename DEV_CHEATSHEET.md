# 🚀 Developer Cheat Sheet

## Quick Commands

| What You Want | Command |
|---------------|---------|
| **Start dev container** | `dev_start.bat` |
| **Stop dev container** | `dev_stop.bat` |
| **Run full test** | `dev_run_test.bat` |
| **Open bash shell** | `dev_shell.bat` |
| **Open Python REPL** | `dev_python.bat` |
| **Open in VS Code** | `code .` |

---

## 🔥 Typical Workflow

```
1. dev_start.bat              ← Start container (once)
2. code .                     ← Open VS Code
3. Edit files                 ← Make changes
4. dev_run_test.bat           ← Test changes
5. Repeat steps 3-4           ← Iterate!
6. dev_stop.bat               ← Stop when done
```

---

## 📝 Files You'll Edit

| File | What It Does |
|------|--------------|
| `audiobook_catalog_config.json` | Add genres, change timespan, adjust settings |
| `audiobook_catalog_crawler.py` | Fix extraction logic, add features |
| `audiobook_catalog_test_runner.py` | Change test behavior, add reports |
| `audiobook_query.py` | Modify CLI interface |

**All changes sync instantly to Docker!**

---

## 🐛 Debugging Toolkit

### Check Screenshots
```bash
explorer catalog_cache\
# Look at: audiobooks_page.png, results_*.png
```

### View Raw HTML
```bash
notepad catalog_cache\raw_results.html
```

### Check Logs
```bash
type audiobook_catalog_test.log
```

### Interactive Python
```bash
dev_python.bat
>>> from audiobook_catalog_crawler import AudiobookCatalogCrawler
>>> crawler = AudiobookCatalogCrawler()
```

### Bash Shell
```bash
dev_shell.bat
# Now you're inside the container
ls -la
python audiobook_query.py
```

---

## ⚙️ Common Config Changes

### Add Genre
```json
{
  "whitelisted_genres": [
    {"name": "Mystery", "value": "15", "enabled": true}
  ]
}
```

### Change to Monthly
```json
{
  "timespan_preference": {
    "value": "4",
    "label": "Last 30 days"
  }
}
```

### Get Top 20
```json
{
  "extraction_settings": {
    "max_results_per_genre": 20
  }
}
```

---

## 🎯 Production vs Development

| Mode | Command | Use Case |
|------|---------|----------|
| **Dev** | `dev_start.bat` + edit + `dev_run_test.bat` | Development, testing |
| **Prod** | `run_docker_catalog_test.bat` | Scheduled runs, final tests |

**Dev = Live editing, Prod = Baked-in code**

---

## 📚 Full Docs

- **Development**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Quick Start**: [QUICKSTART_CATALOG.md](QUICKSTART_CATALOG.md)
- **Complete System**: [CATALOG_SYSTEM_SUMMARY.md](CATALOG_SYSTEM_SUMMARY.md)
- **Docker Details**: [DOCKER_CATALOG_README.md](DOCKER_CATALOG_README.md)

---

## 💡 Pro Tips

1. **Keep container running** during development session
2. **Use VS Code** for best experience
3. **Check screenshots** when extraction fails
4. **Use `dev_shell.bat`** for quick debugging
5. **Stop container** when done to free resources

---

## 🚨 If Something Breaks

```bash
# Nuclear option: Rebuild everything
dev_stop.bat
docker-compose -f docker-compose.catalog.dev.yml build --no-cache
dev_start.bat
```

---

## 🎉 That's It!

Start developing:
```bash
dev_start.bat
code .
```
