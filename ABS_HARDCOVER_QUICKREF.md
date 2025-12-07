# AudiobookShelf ↔ Hardcover Metadata Sync - Quick Reference

## 30-Second Setup

```bash
export AUDIOBOOKSHELF_URL="http://localhost:13378"
export AUDIOBOOKSHELF_API_KEY="your_key"
export HARDCOVER_TOKEN="your_token"
```

## Test Connectivity (2 min)

```bash
python test_abs_hardcover_sync.py
```

## Run Workflows

### Dry-Run (No Changes)
```bash
python abs_hardcover_workflow.py --limit 10
```

### With Audio Validation
```bash
python abs_hardcover_workflow.py --limit 10 --validate-audio
```

### Apply Updates
```bash
python abs_hardcover_workflow.py --limit 10 --auto-update
```

## Validate Audio Files

```bash
# Single file
python validate_audiobooks.py "/path/to/file.m4b" \
    --hardcover-title "Title" \
    --hardcover-author "Author"

# Directory with auto-open
python validate_audiobooks.py \
    --hardcover-title "Title" \
    --hardcover-author "Author" \
    --library-path "/path/to/folder" \
    --auto-open
```

## Workflow Status Meanings

| Status | Meaning | Action |
|--------|---------|--------|
| **unchanged** | Already matches Hardcover | None - data is canonical |
| **updated** | Ready to update (confidence ≥95%) | Apply with --auto-update |
| **pending_verification** | Low confidence (<95%) | Review in ABS UI or validate audio |
| **failed** | Not found in Hardcover | Check Hardcover.app or skip |

## Reports Generated

```bash
# View workflow results
cat abs_hardcover_workflow_report.json

# View audio validation results
cat audiobook_validation_report.json

# Query audit database
sqlite3 abs_hardcover_sync.db \
  "SELECT abs_title, hardcover_title, synced_at FROM sync_history"
```

## Common Issues

### "401 Unauthorized"
```bash
# Get correct ABS API key from http://localhost:13378/settings
# Update environment variable
export AUDIOBOOKSHELF_API_KEY="correct_key"
```

### "Book Not Found"
- Book may not exist in Hardcover.app yet
- Check: https://hardcover.app/search
- If not there, will be marked "failed" in report

### Low Confidence Match
```bash
# Manually validate audio file
python validate_audiobooks.py "/path/to/audiobook.m4b" \
    --hardcover-title "Expected Title" \
    --hardcover-author "Expected Author" \
    --auto-open
```

### ffprobe Not Found
```bash
# Windows (chocolatey)
choco install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

## Performance Tips

1. **Use cache**: Reuse same client connection (done automatically)
2. **Batch process**: Sync large libraries in 500-book chunks
3. **Check cache**: `ls -lh hardcover_cache.db` (should grow, then stabilize)
4. **Monitor API**: Never exceeds 60 req/min (built-in rate limit)

## Decision Tree

```
Need to update audiobook metadata?
  └─ YES → python abs_hardcover_workflow.py --limit 10
            └─ Review report
               └─ Confidence ≥ 95%?
                  ├─ YES → python abs_hardcover_workflow.py --auto-update
                  └─ NO  → python validate_audiobooks.py --auto-open
                           └─ Manually verify
                              └─ python abs_hardcover_workflow.py --auto-update
```

## File Locations

| File | Purpose |
|------|---------|
| `backend/integrations/audiobookshelf_hardcover_sync.py` | Main sync engine |
| `backend/integrations/audio_validator.py` | Audio file validator |
| `abs_hardcover_workflow.py` | Complete workflow (run this) |
| `test_abs_hardcover_sync.py` | Test suite |
| `validate_audiobooks.py` | Audio validator CLI |
| `AUDIOBOOK_METADATA_SYNC_GUIDE.md` | Full documentation |
| `abs_hardcover_sync.db` | Audit database (created on first run) |
| `hardcover_cache.db` | Hardcover cache (created on first run) |

## Environment Variables

| Variable | Value | Source |
|----------|-------|--------|
| `AUDIOBOOKSHELF_URL` | `http://localhost:13378` | Your ABS server |
| `AUDIOBOOKSHELF_API_KEY` | Token from ABS settings | ABS → Settings → API |
| `HARDCOVER_TOKEN` | Bearer token | https://hardcover.app/settings |

## Full Library Workflow

```bash
# Phase 1: Test with 10 books (no updates)
python abs_hardcover_workflow.py --limit 10
# Review: abs_hardcover_workflow_report.json

# Phase 2: Full scan with dry-run
python abs_hardcover_workflow.py
# Review: Check all statuses

# Phase 3: Audio validation for low-confidence
python validate_audiobooks.py \
    --hardcover-title "Title" \
    --hardcover-author "Author" \
    --library-path "/path/to/audiobooks" \
    --auto-open

# Phase 4: Apply all updates
python abs_hardcover_workflow.py --auto-update

# Phase 5: Verify in AudiobookShelf
# Open http://localhost:13378
# Check a few books to confirm updates
```

## Metadata Comparison

```
ABS: "The Way of Kings: Part One"
HC:  "The Way of Kings"
     Result: Partial match (95% confidence)

ABS: "Brandon Sanderson"
HC:  "Brandon Sanderson"
     Result: Exact match (100% confidence)

Average: 97.5% confidence → Auto-update enabled
```

## Confidence Score Guide

| Score | Rating | Action |
|-------|--------|--------|
| 1.0 (100%) | Perfect | Auto-update ✓ |
| 0.95-0.99 | Excellent | Auto-update ✓ |
| 0.90-0.94 | Good | Manual review recommended |
| 0.70-0.89 | Fair | Manual review required |
| <0.70 | Poor | Skip or use audio validation |

## Database Queries

```bash
# Get updates from today
sqlite3 abs_hardcover_sync.db \
  "SELECT abs_title, hardcover_title FROM sync_history WHERE date(synced_at) = date('now')"

# Get high-confidence updates
sqlite3 abs_hardcover_sync.db \
  "SELECT abs_title, confidence FROM sync_history WHERE confidence >= 0.95"

# Get failed resolutions
sqlite3 abs_hardcover_sync.db \
  "SELECT abs_title, abs_author FROM sync_history WHERE hardcover_title IS NULL"
```

## Help & Documentation

| Topic | File |
|-------|------|
| Quick Start | This file (ABS_HARDCOVER_QUICKREF.md) |
| Full Guide | AUDIOBOOK_METADATA_SYNC_GUIDE.md |
| Delivery Summary | AUDIOBOOK_SYNC_DELIVERY.md |
| Troubleshooting | AUDIOBOOK_METADATA_SYNC_GUIDE.md → Troubleshooting |
| Integration | AUDIOBOOK_METADATA_SYNC_GUIDE.md → Integration |

## One-Liner Commands

```bash
# Test everything
python test_abs_hardcover_sync.py && python abs_hardcover_workflow.py --limit 10

# Full library scan
python abs_hardcover_workflow.py

# Update everything
python abs_hardcover_workflow.py --auto-update

# Check audit database
sqlite3 abs_hardcover_sync.db "SELECT COUNT(*) FROM sync_history"

# View cache size
du -h hardcover_cache.db
```

---

**Status**: Production Ready | **Time to Deploy**: 5 minutes | **Time to Sync**: 30 min-2 hours

**Start here**: `python abs_hardcover_workflow.py --limit 10`

