# Audio Verification System - Quick Start Guide

## Prerequisites

1. **Install FFmpeg**
   ```bash
   # Test if installed
   ffmpeg -version
   ```

2. **Install Python packages**
   ```bash
   pip install speechrecognition pydub beautifulsoup4 lxml aiohttp
   ```

3. **Set up environment**
   ```bash
   # Create .env file with:
   ABS_URL=http://localhost:13378
   ABS_TOKEN=your_api_token_here
   ```

## Quick Run

### Process All Uncertain Books
```bash
cd C:\Users\dogma\Projects\MAMcrawler
python verify_all_uncertain_books.py
```

### Test Single Book
```bash
python test_single_book_verification.py
```

### Test Goodreads Client
```bash
python goodreads_api_client.py
```

## Understanding Results

### Auto-Updated Books
Books with **confidence >= 95%** are automatically updated in Audiobookshelf.

Check `verification_summary.txt` for:
- Original title
- Updated title
- New series information
- Confidence score

### Manual Review Needed
Books with **confidence < 95%** are saved to `books_needing_manual_review.json`.

Common reasons:
- Goodreads couldn't find the book
- Title mismatch (speech recognition error)
- Author mismatch (narrator vs author confusion)

## Output Files

| File | Purpose |
|------|---------|
| `verification_results.json` | Complete technical results |
| `verification_summary.txt` | Human-readable summary |
| `verification_audit.log` | Detailed operation log |
| `books_needing_manual_review.json` | Books to review manually |

## Workflow

```
uncertain_books.json
        ↓
Extract 45s audio
        ↓
Transcribe with Google Speech
        ↓
Parse title/author/series
        ↓
Verify with Goodreads
        ↓
Confidence >= 95%?
    ↙         ↘
  YES          NO
    ↓          ↓
Update ABS   Manual Review
```

## Success Metrics

Current run on 4 unique books:
- ✅ Audio extracted: 4/4 (100%)
- ✅ Transcribed: 4/4 (100%)
- ✅ Auto-updated: 2/4 (50%)
- ⚠️  Manual review: 2/4 (50%)

## Common Issues

### "FFmpeg not found"
**Solution:** Install FFmpeg and add to PATH

### "Speech not understood"
**Solution:** Audio quality issue - check audio file

### "No Goodreads results"
**Solution:** Book may not be in Goodreads database

## Next Steps

1. Review `verification_summary.txt`
2. Check auto-updated books in Audiobookshelf
3. Manually process books in `books_needing_manual_review.json`
4. Re-run as needed for new uncertain books

## Support

Check logs for errors:
```bash
type verification_audit.log | more
```

View detailed results:
```bash
# PowerShell
Get-Content verification_results.json | ConvertFrom-Json | Format-List
```
