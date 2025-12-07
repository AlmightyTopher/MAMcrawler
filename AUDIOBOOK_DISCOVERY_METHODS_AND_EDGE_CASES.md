# Audiobook Discovery Methods & Edge Case Handling Guide

**Purpose**: Document all available methods to discover audiobooks and how to handle edge cases when any method fails
**Status**: Comprehensive reference for next workflow run
**Date**: 2025-11-29

---

## Overview: 7 Different Discovery Methods

Instead of hardcoding "get 10 sci-fi and 10 fantasy", the system can dynamically choose from multiple sources:

### Method 1: Prowlarr Curated Lists ✅
**File**: `search_prowlarr_curated_audiobooks_v2.py`
**What it does**: Queries Prowlarr for pre-curated audiobook categories
**Return value**: List of audiobooks with metadata
**Advantage**: Real-time, includes quality ratings, torrent info already available
**Edge case handling**:
- If Prowlarr down → Fall back to Method 2
- If category empty → Try alternative category
- If no results → Log and continue to next category

**Code reference**:
```python
def get_prowlarr_curated():
    categories = ['top-audiobooks', 'newly-released', 'trending', 'bestselling']
    for cat in categories:
        results = prowlarr_query(cat)
        if results:
            return results[:10]
    return []  # All categories failed
```

### Method 2: Popular Audiobooks Search ✅
**File**: `search_popular_audiobooks.py`
**What it does**: Queries Google Books + Goodreads for current popular audiobooks
**Return value**: List of book titles and authors
**Advantage**: Accesses real-time popularity data from multiple sources
**Edge case handling**:
- If Google Books API down → Fall back to Goodreads only
- If rate limited → Wait and retry with exponential backoff
- If no results → Try different search query
- Fallback query: "bestselling audiobooks" → "top rated audiobooks" → "latest audiobooks"

**Code reference**:
```python
def get_popular_audiobooks():
    try:
        return google_books_api.search_popular()
    except GoogleBooksAPIError:
        try:
            return goodreads_api.search_bestsellers()
        except GoodreadsError:
            return fallback_hardcoded_popular_list()
```

### Method 3: Top 10 by Genre Scrape ✅
**File**: `scrape_top10_audiobooks.py`
**What it does**: Scrapes top 10 audiobooks from multiple genre categories
**Return value**: Categorized book lists (sci-fi, fantasy, romance, mystery, etc.)
**Advantage**: Gets diverse genre coverage, comprehensive
**Edge case handling**:
- If website down → Use cached results from last run
- If HTML structure changed → Log error and notify
- If genre page missing → Skip that genre and continue
- Partial scrape: Return whatever was successfully scraped

**Code reference**:
```python
def scrape_top_by_genre():
    genres = ['sci-fi', 'fantasy', 'romance', 'mystery', 'thriller', 'biography']
    results = {}
    for genre in genres:
        try:
            results[genre] = scrape_top10(genre)
        except Exception as e:
            logger.warning(f"Failed to scrape {genre}: {e}")
            results[genre] = []  # Empty, but don't crash
    return results
```

### Method 4: Weekly Trending ✅
**File**: `get_weekly_fantasy_audiobooks.py`
**What it does**: Gets audiobooks trending this week
**Return value**: Trending audiobook list with trend velocity
**Advantage**: Always fresh, catches momentum titles
**Edge case handling**:
- If no weekly data available → Use monthly trending
- If timestamp old (>7 days) → Re-fetch
- If API change breaks parser → Fall back to weekly bestseller list

**Code reference**:
```python
def get_weekly_trending():
    try:
        return goodreads.get_weekly_trending()
    except ParserError:
        logger.info("Weekly trending parser broken, using monthly")
        return goodreads.get_monthly_trending()
    except APIError:
        logger.info("Goodreads API down, using cached data")
        return load_cached_trending()
```

### Method 5: Author Library Expansion ✅
**File**: `author_audiobook_search.py`, `author_complete_search.py`
**What it does**: For each author in current library, get ALL their other books
**Return value**: Complete author bibliographies with missing books flagged
**Advantage**: Ensures series completion, expands from existing library
**Edge case handling**:
- Author has no other books → Mark complete and skip
- Author search returns duplicates → Deduplicate by ISBN
- Author search incomplete → Merge results from multiple sources (Goodreads + Google Books)
- Author disambiguation needed → Try (author + "audiobook") search

**Code reference**:
```python
def expand_author_library():
    library_authors = get_library_authors()
    missing_books = {}

    for author in library_authors:
        try:
            all_books = mam_search(f'author:"{author}"')
            library_books = get_author_books_in_library(author)
            missing = [b for b in all_books if b not in library_books]
            if missing:
                missing_books[author] = missing
        except Exception as e:
            logger.warning(f"Failed to expand {author}: {e}")
            # Continue with next author, don't crash

    return missing_books
```

### Method 6: Series Completion ✅
**File**: `analyze_missing_books_comprehensive.py`, `find_missing_fantasy_audiobooks.py`
**What it does**: For incomplete series, find remaining books
**Return value**: Organized list of missing books by series
**Advantage**: Targeted, user wants complete series not random books
**Edge case handling**:
- Series name ambiguous → Try multiple variations
- Series has multiple authors → Handle properly
- Book numbering inconsistent → Use release order as backup
- No series info found → Treat as standalone

**Code reference**:
```python
def complete_series():
    incomplete_series = find_incomplete_series()
    to_acquire = {}

    for series_name in incomplete_series:
        try:
            all_books = mam_search(f'series:"{series_name}"')
            have = get_series_books_in_library(series_name)
            missing = [b for b in all_books if b not in have]
            if missing:
                to_acquire[series_name] = missing
        except Exception as e:
            # Try alternative search
            try:
                all_books = mam_search(series_name)  # No series: prefix
                missing = [b for b in all_books if b not in have]
                if missing:
                    to_acquire[series_name] = missing
            except:
                logger.warning(f"Series {series_name} not found anywhere")

    return to_acquire
```

### Method 7: Goodreads/Google Books Direct API ✅
**File**: `test_google_books_integration.py`, `dual_goodreads_scraper.py`
**What it does**: Direct API queries to Goodreads and Google Books
**Return value**: Book metadata with ratings and reviews
**Advantage**: Highest quality metadata, can filter by rating/reviews
**Edge case handling**:
- API key invalid/expired → Try backup key or skip
- Rate limit hit → Implement exponential backoff with jitter
- Book not found → Log but continue
- Response malformed → Retry with different query format

**Code reference**:
```python
def api_discovery():
    books = []

    for query in ['bestselling audiobooks', 'top rated audiobooks', 'popular fantasy']:
        try:
            results = google_books.search(query, filters={'ebook': 'audiobook'})
            books.extend(results)
        except RateLimitError:
            logger.info("Rate limited, waiting before retry")
            time.sleep(60)
            try:
                results = google_books.search(query)
                books.extend(results)
            except Exception as e:
                logger.warning(f"Query '{query}' failed: {e}")
        except Exception as e:
            logger.warning(f"Query '{query}' failed: {e}")
            continue

    return deduplicate_books(books)
```

---

## Edge Case Decision Tree

### Decision Matrix: What to Do When Discovery Method Fails

```
ENTRY POINT: Need to discover audiobooks
  ↓
TRY Method 1 (Prowlarr Curated)
  ├─ SUCCESS → Return results, goto SEARCH_MYRIAD
  ├─ TIMEOUT → Log failure, TRY Method 2
  ├─ INVALID RESPONSE → Log error, TRY Method 2
  └─ NO RESULTS → TRY Method 2

TRY Method 2 (Popular Audiobooks)
  ├─ SUCCESS → Return results, goto SEARCH_MYRIAD
  ├─ RATE LIMITED → Wait exponential backoff, RETRY once
  ├─ API KEY INVALID → Log critical error, TRY Method 3
  └─ NO RESULTS → TRY Method 3

TRY Method 3 (Top 10 Genre Scrape)
  ├─ SUCCESS (partial or full) → Return whatever scraped, goto SEARCH_MYRIAD
  ├─ WEBSITE DOWN → Use cached from yesterday, goto SEARCH_MYRIAD
  ├─ PARSER BROKEN → Log error, TRY Method 4
  └─ NO RESULTS → TRY Method 4

TRY Method 4 (Weekly Trending)
  ├─ SUCCESS → Return results, goto SEARCH_MYRIAD
  ├─ DATA STALE → Check if >7 days, if so RETRY
  ├─ NO WEEKLY DATA → Use monthly instead, goto SEARCH_MYRIAD
  └─ ALL FAIL → TRY Method 5

TRY Method 5 (Author Expansion)
  ├─ SUCCESS (partial or full) → Return results, goto SEARCH_MYRIAD
  ├─ SOME AUTHORS FAIL → Return successful ones, skip failed
  ├─ ALL AUTHORS FAIL → TRY Method 6
  └─ NO MISSING BOOKS → Log info, TRY Method 6

TRY Method 6 (Series Completion)
  ├─ SUCCESS (partial or full) → Return results, goto SEARCH_MYRIAD
  ├─ SOME SERIES FAIL → Return successful ones, skip failed
  ├─ ALL SERIES COMPLETE → Log success, goto NEXT_PHASE
  └─ ALL FAIL → TRY Method 7

TRY Method 7 (Direct API)
  ├─ SUCCESS → Return results, goto SEARCH_MYRIAD
  ├─ RATE LIMITED → Backoff, RETRY once
  ├─ ALL API FAIL → Use hardcoded fallback, goto SEARCH_MYRIAD
  └─ NO RESULTS → Log warning, goto NEXT_PHASE

FALLBACK: Hardcoded list
  ├─ If ALL discovery methods fail
  ├─ Use: Top 10 sci-fi, Top 10 fantasy (original system)
  └─ Log critical: "All discovery methods failed, using hardcoded"

SEARCH_MYRIAD:
  ├─ Take discovered books
  ├─ Search MAM for each title
  ├─ Get magnet links
  └─ Add to qBittorrent

NEXT_PHASE:
  ├─ Download complete
  ├─ Sync to AudiobookShelf
  ├─ Update metadata
  └─ Repeat for series/authors
```

---

## Implementation Strategy: Adaptive Discovery

### Execution Flow for Next E2E Run

```python
def adaptive_book_discovery():
    """
    Try multiple discovery methods until one succeeds
    Return best available results, never fail
    """

    discovered_books = []
    discovery_methods = [
        ('Prowlarr Curated', discover_prowlarr_curated),
        ('Popular Audiobooks', discover_popular),
        ('Genre Top 10', discover_genre_top10),
        ('Weekly Trending', discover_weekly_trending),
        ('Author Expansion', discover_author_expansion),
        ('Series Completion', discover_series_completion),
        ('Direct APIs', discover_direct_apis),
    ]

    methods_tried = []

    for method_name, method_func in discovery_methods:
        try:
            logger.info(f"Trying discovery method: {method_name}")
            results = method_func()

            if results:
                logger.info(f"✓ {method_name} succeeded: {len(results)} books found")
                discovered_books.extend(results)
                methods_tried.append((method_name, 'SUCCESS', len(results)))
                break  # First successful method wins
            else:
                logger.info(f"✗ {method_name} returned no results")
                methods_tried.append((method_name, 'NO_RESULTS', 0))
                continue  # Try next method

        except Exception as e:
            logger.warning(f"✗ {method_name} failed: {e}")
            methods_tried.append((method_name, 'ERROR', str(e)))
            continue  # Try next method

    if not discovered_books:
        logger.critical("All discovery methods failed, using hardcoded fallback")
        discovered_books = get_hardcoded_fallback_books()
        methods_tried.append(('Hardcoded Fallback', 'FALLBACK', len(discovered_books)))

    # Log all attempts for next run's reference
    log_discovery_attempt(methods_tried)

    return discovered_books
```

---

## Logging & State Management for Next Run

### What Gets Saved for Next Execution

**File**: `discovery_state.json`
```json
{
  "last_run": "2025-11-29T10:00:00Z",
  "methods_tried": [
    {
      "method": "Prowlarr Curated",
      "status": "SUCCESS",
      "books_found": 12,
      "execution_time_ms": 342,
      "error": null
    },
    {
      "method": "Popular Audiobooks",
      "status": "SKIPPED",
      "books_found": 0,
      "execution_time_ms": 0,
      "error": null
    }
  ],
  "total_discovered": 12,
  "total_execution_time_ms": 342,
  "fallback_used": false,
  "cache_hit": false,
  "next_run_recommendation": "Prowlarr Curated still working, start with that"
}
```

### Edge Case Reference for Next Run

**File**: `edge_cases_encountered.md`
```markdown
## Edge Cases from Previous Run

### Run Date: 2025-11-29

#### Prowlarr Curated
- Status: Working
- Response time: 342ms
- Empty categories: none
- Note: All categories returned results

#### Popular Audiobooks
- Status: Skipped (Prowlarr succeeded)
- Would have used fallback: false
- Note: Not tested this run

#### Series Completion
- Status: Not needed (Author expansion found 47 books)
- Note: Authors had sufficient missing books

#### What Failed Last Time (if anything)
- [None this run - all systems operational]

#### What to Watch For Next Run
- Google Books API rate limits (hit on run 2025-11-28)
- Prowlarr categorization changes (check if structure changed)
- MAM search timeouts (experienced on large result sets)
```

---

## Quick Reference: Which Method to Use When

| Situation | Recommended Method | Fallback | Edge Case |
|-----------|-------------------|----------|-----------|
| **Fresh discovery** | Prowlarr Curated | Popular Audiobooks | If all fail: Hardcoded sci-fi/fantasy |
| **Need trendy books** | Weekly Trending | Popular Audiobooks | If stale >7 days, use Monthly |
| **Expand library** | Author Expansion | Series Completion | If author not found, try fuzzy match |
| **Complete series** | Series Completion | Author Expansion | If series ambiguous, try multiple names |
| **Discovery failed** | Direct APIs | Hardcoded | Log critical error for debugging |
| **All methods fail** | Hardcoded Fallback | Manual intervention | Never return empty, always try fallback |

---

## Testing Edge Cases Before E2E

**Recommended pre-flight checks** (should be automated):

```python
def preflight_discovery_check():
    """Run before full E2E to catch issues early"""

    checks = {
        'Prowlarr API': check_prowlarr_api(),
        'Google Books API': check_google_books_api(),
        'Goodreads API': check_goodreads_api(),
        'MAM Login': check_mam_login(),
        'Scrape Parser': check_scrape_parser(),
        'Cache Available': check_cache_exists(),
        'Network': check_internet_connection(),
    }

    failures = {k: v for k, v in checks.items() if not v}

    if failures:
        logger.warning(f"Preflight issues: {failures}")
        return False

    logger.info("All preflight checks passed")
    return True
```

---

## How to Add New Discovery Methods

**Template for future discovery sources**:

```python
def discover_[new_source]():
    """
    Discover audiobooks from [new source]

    Returns:
        List[Dict]: Book metadata
        - title (required)
        - author (required)
        - source (required)
        - url (optional)
        - rating (optional)
        - reviews (optional)

    Raises:
        [CustomException]: If source unreachable or returns unexpected format

    Edge cases handled:
        - Source timeout
        - No results found
        - Malformed response
        - Rate limit
        - Authentication failure
    """

    try:
        # Implementation
        results = query_source()
        return format_results(results)
    except SourceTimeoutError as e:
        logger.warning(f"Source timeout: {e}")
        return []
    except SourceAuthError as e:
        logger.error(f"Auth failed: {e}")
        raise
    except SourceFormatError as e:
        logger.error(f"Response format unexpected: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
```

---

## Next E2E Run: Complete Plan

### Phase 1: Preflight (5 min)
- Run all preflight checks
- Load discovery state from last run
- Determine which discovery method to try first

### Phase 2: Book Discovery (10-30 min depending on method)
- Try Method 1 (Prowlarr Curated) - estimate 5 min
- If fails, try Method 2-7 in order
- Log all attempts
- Save state for next run

### Phase 3: MAM Search (10-30 min)
- Search MAM for each discovered book
- Get magnet links
- Log all searches and results
- Handle cases where book not found on MAM

### Phase 4: qBittorrent Addition (5-10 min)
- Add magnet links to qBittorrent
- Monitor for qBit failures
- If qBit fails, use queue file

### Phase 5-7: Download, Sync, Metadata (4+ hours)
- Monitor download progress
- Sync completed files to AudiobookShelf
- Update metadata (authors, narrators, genres)

### Phase 8: Analysis (20-30 min)
- Check series completeness
- If incomplete: repeat Phases 2-7 for missing books
- Check author coverage
- If gaps: repeat Phases 2-7 for missing author books

### Phase 9: Reporting (10 min)
- Generate final statistics
- Document what worked/failed
- Save state for next run
- Update edge_cases_encountered.md

---

**This document serves as a reference for handling ANY discovery method failure gracefully and intelligently choosing alternatives.**

*Last Updated: 2025-11-29*
*Next E2E Run: Use this document to handle edge cases intelligently*
