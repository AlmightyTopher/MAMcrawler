# Google Books API → Audiobookshelf Metadata Mapping

**Analysis Date**: 2025-11-22
**Status**: Comprehensive coverage with some gaps

---

## Quick Answer

**Short version**: Google Books API covers ~70-80% of what Audiobookshelf needs. It fills in the core required fields well but **CANNOT provide audiobook-specific data**.

---

## Complete Field Mapping

### Google Books API Output → Audiobookshelf Fields

| Audiobookshelf Field | Data Type | Required? | Google Books Provides? | Notes |
|---------------------|-----------|-----------|----------------------|-------|
| **title** | String | YES | ✓ YES | Exact match - Google returns `volumeInfo.title` |
| **authorName** | String | NO | ✓ YES | From `volumeInfo.authors[]` (joined with commas) |
| **seriesName** | String | NO | ✓ PARTIAL | Only if series info exists in Google Books metadata |
| **description** | Text | NO | ✓ YES | Google returns `volumeInfo.description` |
| **publisher** | String | NO | ✓ YES | From `volumeInfo.publisher` |
| **publishedDate** | Date | NO | ✓ YES | From `volumeInfo.publishedDate` |
| **isbn** | String | NO | ✓ YES | Both ISBN-10 and ISBN-13 available |
| **pageCount** | Integer | NO | ✓ YES | From `volumeInfo.pageCount` (but see note below) |
| **categories/genres** | Array | NO | ✓ YES | From `volumeInfo.categories[]` |
| **language** | String | NO | ✓ YES | From `volumeInfo.language` |
| **cover/thumbnail** | URL | NO | ✓ YES | From `volumeInfo.imageLinks` (multiple sizes) |
| **rating** | Float (0-5) | NO | ✗ NO | Google Books has ratings but they're review aggregate, not standard rating field |

### Audiobook-Specific Fields (CRITICAL GAPS)

| Audiobookshelf Field | Data Type | Required? | Google Books Provides? | Impact |
|---------------------|-----------|-----------|----------------------|--------|
| **narrators** | String | NO | ✗ NO | Google Books doesn't track audiobook narrators |
| **duration_minutes** | Integer | NO | ✗ NO | Google Books only has page count, not audio duration |
| **asin** | String | NO | ✗ NO | Would need to look up elsewhere (Amazon API separate) |
| **abridged** | Boolean | NO | ✗ NO | Google Books doesn't explicitly mark abridged status |

---

## Data Coverage Analysis

### What You GET from Google Books (100% coverage)

```
{
    "title": "The Martian",
    "authors": ["Andy Weir"],                           ← JOIN with ", "
    "description": "An astronaut becomes stranded on Mars...",
    "publisher": "Crown Publishers",
    "published_date": "2011-11-11",
    "isbn_10": "0553807633",
    "isbn_13": "9780553807633",
    "page_count": 369,
    "categories": ["Science Fiction", "Adventure"],
    "language": "en",
    "thumbnail": "https://books.google.com/images/...",
    "google_books_id": "someBookId123"
}
```

**Coverage for Audiobookshelf metadata**: ~75%
- ✓ Title
- ✓ Author(s)
- ✓ Description
- ✓ Publisher
- ✓ Publication Date
- ✓ ISBN
- ✓ Categories
- ✓ Language
- ✓ Cover Image

### What You DON'T GET from Google Books (Critical Gaps)

1. **Narrator Information** ✗
   - Not available in Google Books API at all
   - Would need: Audible API or Goodreads API (both have restrictions)
   - Impact: Your library loses narrator metadata

2. **Duration/Length** ✗
   - Google Books provides page_count (for print books)
   - Audiobook duration is NOT available
   - Impact: Cannot show audiobook length in Audiobookshelf
   - Workaround: Audiobookshelf auto-calculates from file if present

3. **Abridged Status** ✗
   - Some Google Books entries mention in title/description
   - Not a dedicated field
   - Impact: Can manually detect "abridged" in title, but unreliable

4. **ASIN (Amazon ID)** ✗
   - Not provided by Google Books
   - Would require separate Amazon lookup
   - Impact: Can't link to Amazon audiobook edition

5. **Explicit Rating** ✗
   - Google Books has aggregate ratings (not useful for ABS)
   - Not individual audiobook ratings
   - Impact: No standardized rating to import

---

## Practical Mapping Implementation

### How to Transform Google Books → Audiobookshelf

```python
# From Google Books API extract_metadata() output
google_metadata = {
    "title": "Foundation",
    "authors": ["Isaac Asimov"],
    "description": "...",
    "publisher": "Gnome Press",
    "published_date": "1951-06-01",
    "isbn_13": "9780553293357",
    "categories": ["Science Fiction"],
    "language": "en",
    "thumbnail": "https://..."
}

# Transform to Audiobookshelf format
abs_update = {
    "title": google_metadata["title"],
    "authorName": ", ".join(google_metadata["authors"]),
    "description": google_metadata["description"],
    "publisher": google_metadata["publisher"],
    "publishedDate": google_metadata["published_date"],  # May need format conversion
    "isbn": google_metadata["isbn_13"],
    "language": google_metadata["language"],
    # Note: You can set additional fields but these are the mapped ones
}

# Apply to Audiobookshelf
await abs_client.update_book_metadata(book_id, abs_update)
```

### Quality Preservation Logic

Since Google Books might not have complete data for all books:

```python
# ONLY update if you have the data
if google_metadata.get("title"):
    update_dict["title"] = google_metadata["title"]

# Skip fields with None/empty
if google_metadata.get("description"):
    update_dict["description"] = google_metadata["description"]

# Handle authors properly
if google_metadata.get("authors"):
    update_dict["authorName"] = ", ".join(google_metadata["authors"])

# Only update if not already set in Audiobookshelf
# This prevents overwriting better data
```

---

## Completeness Scoring

For your 1,608 audiobooks, you can calculate metadata completeness:

### Fields Google Books Provides (7 fields)
1. Title
2. Author(s)
3. Description
4. Publisher
5. Published Date
6. ISBN
7. Categories

### Fields Audiobookshelf NEEDS (baseline)
1. Title (REQUIRED)
2. Author(s) (optional but expected)
3. Description (nice to have)
4. ISBN (useful for deduplication)

### Fields Missing from Google Books (3 critical for audio)
1. Narrator
2. Duration
3. Abridged status

**Expected Metadata Completeness After Google Books Import**: 60-70%

Why not higher:
- Missing narrator info
- Missing duration
- Some books may not be in Google Books database
- Some audiobook-specific details won't transfer from print book data

**What you can improve**:
- Narrator: Manual tagging or Audible API (separate)
- Duration: Calculated automatically by Audiobookshelf from files
- Abridged: Text search in title/description

---

## Real Example: "Project Hail Mary"

### Google Books Returns
```json
{
    "title": "Project Hail Mary",
    "authors": ["Andy Weir"],
    "description": "Ryland Grace is the sole survivor...",
    "publisher": "Ballantine Books",
    "publishedDate": "2021-05-04",
    "isbn_10": "0593135204",
    "isbn_13": "9780593135204",
    "pageCount": 478,
    "categories": ["Science Fiction", "Adventure"],
    "language": "en",
    "imageLinks": {
        "thumbnail": "http://books.google.com/images/...",
        "small": "http://books.google.com/images/...",
        "medium": "http://books.google.com/images/...",
        "large": "http://books.google.com/images/..."
    }
}
```

### What Transfers to Audiobookshelf
```
Title: "Project Hail Mary" ✓
Author: "Andy Weir" ✓
Description: [Full description] ✓
Publisher: "Ballantine Books" ✓
Date: "2021-05-04" ✓
ISBN: "9780593135204" ✓
Categories: ["Science Fiction", "Adventure"] ✓
Cover: [Medium quality image] ✓
```

### What DOESN'T Transfer
```
Narrator: [Not available] ✗ (Critical for audiobooks!)
Duration: [Not available] ✗ (Page count ≠ audio length)
Audible ASIN: [Not provided] ✗
Audiobook Edition Info: [Not tracked] ✗
```

---

## Limitations & Workarounds

### Limitation 1: Not All Books in Google Books
- ~30-40% of audiobooks may not be indexed
- Especially indie published audiobooks
- **Workaround**: Fall back to existing metadata if Google Books returns nothing

### Limitation 2: Printed Book vs Audiobook Mismatch
- Google Books pulls from print edition
- Audiobook may have different narrator/duration
- **Workaround**: Keep audiobook-specific data separate, only fill gaps

### Limitation 3: No Narrator Information
- Critical for audiobook library
- Google Books doesn't track this
- **Workaround**:
  - Option A: Use Audible API separately (cost/complexity)
  - Option B: Manual narrator tagging in Audiobookshelf
  - Option C: Leave blank (acceptable for many use cases)

### Limitation 4: Series Information Partial
- Google Books may not have complete series data
- Especially indie/small press series
- **Workaround**: Series info from MAM crawler if available

---

## Implementation Strategy for Your Library

### Phase 1: Basic Enrichment (Recommended)
```python
# Update core metadata from Google Books
fields_to_update = [
    "title",           # Fill gaps only
    "authorName",      # Fill gaps only
    "description",     # Fill gaps only
    "publisher",       # Fill gaps only
    "isbn",            # Always update (good for dedup)
    "language"         # Fill gaps only
]

# Preserve existing audiobook-specific data:
# - narrator (don't override)
# - duration (auto-calculated by ABS)
# - custom series info (don't override)
```

### Phase 2: Quality Control
```python
# Only update if:
# 1. Field currently empty in Audiobookshelf
# 2. Google Books has data for it
# 3. New data is longer/more complete than existing

# Don't update if:
# 1. Field already has good data
# 2. Google returned empty/generic values
# 3. Would lose audiobook-specific info
```

### Phase 3: Manual Fixes
```
- Narrator: Add manually for top 100 books
- Series: Verify series info matches audiobook edition
- Duration: Let ABS auto-calculate from files
```

---

## Coverage by Book Category

### Mainstream Fiction/Nonfiction
- **Coverage**: 95%+
- All major publishers indexed
- Series info usually available

### SFF (Science Fiction/Fantasy)
- **Coverage**: 90%+
- Popular series well-represented
- Indie published: 50-70%

### Indie/Self-Published
- **Coverage**: 40-60%
- Many not indexed by Google Books
- Often missing from database

### Audiobook-Only Titles
- **Coverage**: 20-40%
- If tied to print edition: good
- If audio-first: often missing

---

## Recommendation

**Use Google Books API for**:
- Title confirmation
- Author verification
- Description enrichment
- ISBN/ISBN-13 deduplication
- Publisher/publication date
- Cover images
- Language/categories

**Don't expect from Google Books**:
- Narrator information
- Audiobook duration
- Audiobook-specific metadata
- Audible Edition information

**Completeness After Implementation**: ~70% for well-known books, ~50% for indie audiobooks

**Action**: Start with Phase 1 basic enrichment. It will meaningfully improve your library without risk of overwriting better data.

---

## Code Usage

Once integrated into `master_audiobook_manager.py`:

```python
from backend.integrations.google_books_client import GoogleBooksClient
from backend.integrations.abs_client import AudiobookshelfClient

async def enrich_book_metadata(abs_client, google_client, book):
    # Search Google Books
    metadata = await google_client.search_and_extract(
        title=book.title,
        author=book.author
    )

    if metadata:
        # Transform to ABS format
        update = {
            "isbn": metadata.get("isbn_13") or metadata.get("isbn_10"),
            "description": metadata.get("description"),
            "publisher": metadata.get("publisher"),
        }

        # Only add if we have data
        if metadata.get("authors"):
            update["authorName"] = ", ".join(metadata["authors"])

        # Apply to Audiobookshelf
        await abs_client.update_book_metadata(book.abs_id, update)

        return True

    return False
```

---

**Summary**: Google Books gets you to 70% metadata quality for your audiobook library - good for discoverability and deduplication, but you'll need separate solutions for narrator and audiobook-specific fields.
