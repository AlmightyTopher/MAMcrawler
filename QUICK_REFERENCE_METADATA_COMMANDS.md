# Quick Reference: Metadata & Series Linking Commands

## After Randi Darren Books Download

### Option 1: Fast API-Based Update (Audiobookshelf Must Be Running)
```bash
python update_audiobooks_metadata.py
```
- Time: ~2-3 minutes
- Creates series groupings automatically
- Works while Audiobookshelf is running
- **USE THIS** if you want the quickest result

### Option 2: Direct Database Update (Audiobookshelf Must Be STOPPED)
```bash
# Step 1: Stop Audiobookshelf completely (close window/service)
# Step 2: Wait 10 seconds for database to unlock
# Step 3: Run this command:
python populate_series_from_metadata.py

# Step 4: Start Audiobookshelf again
```
- Time: ~1-2 minutes
- Most reliable method
- **USE THIS** if database approach preferred or API has issues
- Detailed log file: `populate_series_from_metadata.log`

### Option 3: Enrich Missing Metadata (Optional)
```bash
python metadata_enrichment_service.py
```
- Time: ~5-10 minutes
- Fills in missing author/narrator/description
- Uses Google Books API
- **USE THIS** if books have incomplete metadata after download
- Run after Option 1 or 2

### Verify Series Are Linked
```bash
python verify_series_metadata.py
```
- Time: <1 minute
- Shows sample of books with series info
- Confirms series population worked
- **USE THIS** to verify setup before/after

---

## Expected Results

### Before Running Scripts
```
Books library:
  - Remnant (file: 01 Randi Darren - Remnant I.m4b)
  - Remnant II (file: 02 Randi Darren - Remnant II.m4b)
  - Remnant III (file: 03 Randi Darren - Remnant III.m4b)
  ← NO series grouping, books not linked
```

### After Running Scripts
```
Series: Remnant
  ├─ Remnant (#1)
  ├─ Remnant II (#2)
  └─ Remnant III (#3)

Series: Wild Wastes
  ├─ Wild Wastes (#1)
  ├─ Eastern Expansion (#2)
  ├─ Southern Storm (#3)
  ├─ Wild Wastes 4
  ├─ Wild Wastes 5
  └─ Wild Wastes 6
  ← Click series name to see all books grouped
```

---

## Metadata Fields Being Updated

```json
{
  "title": "Remnant",                    // Book title
  "author": "Randi Darren",              // Author
  "series": "Remnant",                   // Series name (main field for grouping)
  "seriesSequence": "1",                 // Position: 1, 2, 3...
  "narrator": "Michael Kramer",          // Narrator
  "publishedYear": 2020,                 // Year
  "description": "..."                   // Full description
}
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Database locked error | Audiobookshelf still running | Stop Audiobookshelf first, wait 10 sec |
| API connection error | Audiobookshelf not running | Start Audiobookshelf first |
| Series not appearing in UI | Scripts didn't run or failed | Check log files, run verification script |
| Books missing metadata | Torrents had poor metadata | Run enrichment service for Google Books data |
| Book titles are filenames | Metadata extraction failed | Run `update_audiobooks_metadata.py` to fix |

---

## File Locations & Logs

```
Scripts:
  - update_audiobooks_metadata.py (API method)
  - populate_series_from_metadata.py (Database method)
  - metadata_enrichment_service.py (Enhancement)
  - verify_series_metadata.py (Verification)

Database:
  C:\Users\dogma\AppData\Local\Audiobookshelf\config\absdatabase.sqlite

Logs:
  - populate_series_from_metadata.log (from database method)
  - logs/metadata_update.log (from API method)
  - console output (from enrichment service)
```

---

## Randi Darren Series Expected (17 Books Queued)

| Series | Books Queued | Total | Status |
|--------|--------------|-------|--------|
| Wild Wastes | 6 | 6 | 100% Complete |
| System Overclocked | 2 | 2 | 100% Complete |
| Fostering Faust | 3 | 4 | 75% (1 compilation missing) |
| Remnant | 3 | 4 | 75% (1 compilation missing) |
| Incubus Inc. | 2-3 | 4 | 50-75% (varying availability) |
| Privateer's Commission | 0 | 2 | 0% (not available) |
| **TOTAL** | **17** | **26** | **65.4%** |

---

## Next Steps

1. **Wait** for downloads to complete (monitor qBittorrent)
2. **Check** Audiobookshelf Books library to confirm imports
3. **Choose** Option 1 or 2 from above
4. **Run** the script
5. **Verify** in Audiobookshelf UI (click on series name)
6. **Done!**

---

## Contact Points

- Audiobookshelf Web UI: http://localhost:13378
- qBittorrent: http://192.168.0.48:52095/
- Prowlarr: http://localhost:9696/ (used for searching)

---

**Last Updated:** 2025-11-26
**For:** Randi Darren audiobook metadata organization
**Reference:** Full details in `POST_DOWNLOAD_METADATA_WORKFLOW.md`
