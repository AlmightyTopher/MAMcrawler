# Audio Verification Workflow

## Complete Metadata Management System for Audiobookshelf

This document outlines the complete workflow for identifying, analyzing, and correcting audiobook metadata using the actual audio content as the source of truth.

---

## Workflow Overview

```
Step 1: Analyze Confidence
        ↓
Step 2: Identify Uncertain Books
        ↓
Step 3: Listen to Audiobooks
        ↓
Step 4: Apply Corrections
        ↓
Step 5: Verify in UI
```

---

## Step 1: Analyze Confidence of Existing Metadata

**Script**: `audiobook_metadata_extractor.py`

This script scans all 1,700 books and calculates a confidence score (0-1) for each book's metadata. Books below 98% confidence are flagged for verification.

### How Confidence is Calculated:

The confidence analyzer checks for:
- **File format indicators** in titles (MP3, mp3, .m4b, etc.) - These don't belong in titles
- **Malformed characters** or encoding issues
- **Author names embedded in title** - Indicates OCR or parsing errors
- **Series information mismatch** - If series name appears in title but not in metadata
- **Suspicious patterns** - Ellipsis (...), double punctuation, all caps

### Running the Analysis:

```bash
cd C:\Users\dogma\Projects\MAMcrawler
python audiobook_metadata_extractor.py
```

### Output:
- `audiobook_metadata_analysis.log` - Detailed analysis log
- `uncertain_books.json` - List of books with < 98% confidence

### Example Results:

```
Books scanned:            1700
Books needing verification: 68

Books with low confidence (< 98%):
  [86.0%] Terminator Gene - Ian Irvine (MP3)
  [86.0%] Neven Iliev - Everybody Loves Large Chests, Vol. 10 - Law mp3
  [86.0%] Eric Ugland (2022) Wild Wild Quest - The Good Guys, Book 12
  [86.0%] Craig Alanson - Freefall Expeditionary Force Mavericks, Book 2.MP3
```

---

## Step 2: Identify and List Uncertain Books

**Script**: `prepare_audio_verification.py`

This script prepares a manifest of uncertain books, including file paths and metadata, ready for audio verification.

```bash
python prepare_audio_verification.py
```

### Output:
- `audio_verification_manifest.json` - Detailed book information with file locations

---

## Step 3: Manual Audio Verification

For each uncertain book, listen to the opening 30-60 seconds where the narrator announces:
- Book title
- Author name
- Series name (if applicable)
- Book number in series

### Option A: GUI Verification (Easy)

1. Open Audiobookshelf: http://localhost:13378
2. Find the uncertain book in your library
3. Click the book
4. Click "Play" → Listen to first 30-60 seconds
5. Note the correct: Title, Author, Series Name, Series Number
6. Click "Edit" → Update the fields → Save

### Option B: Programmatic Verification

Create a `verification_data.json` file with the correct information:

```json
[
  {
    "book_id": "cd97fca8-a351-4e53-8098-7afda1a80a90",
    "title": "Terminator Gene",
    "author": "Ian Irvine",
    "series_name": "Terminator Gene",
    "sequence": "1"
  },
  {
    "book_id": "9a71b4c0-eccf-4f0b-947e-138f65495409",
    "title": "Everybody Loves Large Chests",
    "author": "Neven Iliev",
    "series_name": "Everybody Loves Large Chests",
    "sequence": "10"
  }
]
```

---

## Step 4: Apply Corrections from Audio Verification

**Script**: `update_from_verification.py`

This script updates the Audiobookshelf metadata with the verified information.

### Using a JSON File:

1. Create `verification_data.json` with verified metadata
2. Run:
```bash
python update_from_verification.py
```

### Interactive Mode:

If no `verification_data.json` exists, the script goes interactive:

```bash
python update_from_verification.py

Interactive Verification Mode
============================================================
Book ID (or 'done' to finish): cd97fca8-a351-4e53-8098-7afda1a80a90
Title (leave blank to skip): Terminator Gene
Author (leave blank to skip): Ian Irvine
Series Name (leave blank to skip): Terminator Gene
Series Number (leave blank to skip): 1

✓ Added: {'book_id': 'cd97fca8...', 'title': 'Terminator Gene', ...}

Book ID (or 'done' to finish): done
```

### Output:
- `update_from_verification.log` - Details of all updates applied

---

## Step 5: Verify in Audiobookshelf UI

After updates are applied:

1. Open http://localhost:13378
2. Find each corrected book
3. Verify the title, author, and series are now correct
4. If not, re-run Step 3 with corrected information

---

## Automatic Metadata Cleaning (Optional)

**Script**: `clean_malformed_metadata.py`

Attempts to automatically clean obvious formatting issues (but requires audio verification for correctness):

```bash
python clean_malformed_metadata.py
```

This script:
- Removes file format indicators from titles
- Attempts to extract author names from titles
- Attempts to extract series information
- Does NOT modify metadata without human verification

---

## Available Scripts

### Analysis & Identification

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `audiobook_metadata_extractor.py` | Analyze confidence of all book metadata | None (reads from API) | `uncertain_books.json` |
| `prepare_audio_verification.py` | Prepare manifest for audio review | `uncertain_books.json` | `audio_verification_manifest.json` |

### Correction & Verification

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `clean_malformed_metadata.py` | Auto-clean obvious formatting issues | `uncertain_books.json` | Metadata updates (API) |
| `audiobook_metadata_corrector.py` | Speech recognition integration (template) | Audio files | Metadata updates (API) |
| `update_from_verification.py` | Apply manual corrections | `verification_data.json` or interactive | Metadata updates (API) |

### Integration Scripts

| Script | Purpose |
|--------|---------|
| `populate_series_array.py` | Initial series population (already run) |
| `fix_series_sequence_from_title.py` | Fix sequence mismatches |
| `fix_series_from_subtitles.py` | Extract series from subtitles |

---

## Current Status

### Completed ✅

1. **Series Population**: All 1,700 books now have series metadata
2. **Subtitle Extraction**: 34 books had additional series info from subtitles
3. **Confidence Analysis**: Identified 68 uncertain books (4 unique entries)
4. **Infrastructure**: Complete verification workflow built

### In Progress / Pending

1. **Manual Verification**: Listen to 4 uncertain books and verify metadata
2. **Corrections**: Apply verified metadata using `update_from_verification.py`
3. **Validation**: Confirm all books display correctly in Audiobookshelf UI

---

## Detailed Book Descriptions (For Reference)

### Book 1: Terminator Gene

- **Current Metadata**: `Terminator Gene - Ian Irvine (MP3)`
- **Issues**: File format in title, author embedded
- **Action**: Listen to book, verify actual title and series name

### Book 2: Everybody Loves Large Chests

- **Current Metadata**: `Neven Iliev - Everybody Loves Large Chests, Vol. 10 - Law mp3`
- **Issues**: File format in title, author embedded, confusing series info
- **Likely**: Series is "Everybody Loves Large Chests" #10

### Book 3: Wild Wild Quest

- **Current Metadata**: `Eric Ugland (2022) Wild Wild Quest - The Good Guys, Book 12`
- **Issues**: Two potential titles mentioned
- **Likely**: "Wild Wild Quest" is title, "The Good Guys" is series #12

### Book 4: Expeditionary Force Mavericks

- **Current Metadata**: `Craig Alanson - Freefall Expeditionary Force Mavericks, Book 2.MP3`
- **Issues**: File format in title, author embedded, ambiguous title
- **Likely**: "Freefall: Expeditionary Force Mavericks" is the full title

---

## Troubleshooting

### Books won't update

- Verify ABS_TOKEN in `.env` is still valid
- Check Audiobookshelf is running: http://localhost:13378
- Check API response: `curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:13378/api/libraries`

### Can't find a book

- Use book_id to query directly:
```bash
python -c "
import asyncio, aiohttp, json, os
async def check():
    token = open('.env').read().split('ABS_TOKEN=')[1].split()[0]
    async with aiohttp.ClientSession(headers={'Authorization': f'Bearer {token}'}) as s:
        async with s.get('http://localhost:13378/api/items/BOOK_ID') as r:
            data = await r.json()
            print(json.dumps(data['media']['metadata'], indent=2))
asyncio.run(check())
"
```

Replace `BOOK_ID` with the actual book ID.

### Speech recognition not working

Install required dependencies:
```bash
pip install pydub speech_recognition librosa
# Also install ffmpeg (system package)
```

---

## Next Steps

1. **Run the analysis** (if not already done):
   ```bash
   python audiobook_metadata_extractor.py
   ```

2. **Listen to the 4 uncertain books** in Audiobookshelf (30-60 seconds each)

3. **Create verification_data.json** with correct metadata

4. **Apply corrections**:
   ```bash
   python update_from_verification.py
   ```

5. **Verify in UI** at http://localhost:13378

---

*Metadata Management System for Audiobookshelf*
*Using Audio Content as the Source of Truth*
*Created: 2025-11-17*
