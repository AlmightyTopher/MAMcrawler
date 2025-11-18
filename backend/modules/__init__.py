"""
Backend Modules - Wrapper functions for existing project scripts

This package provides async-compatible wrapper functions that adapt
existing project scripts for use by the FastAPI backend.

All functions are designed to:
- Work with SQLAlchemy database sessions
- Return structured result dictionaries
- Handle errors gracefully
- Log all activity to database Task records
- Support async/await patterns

Modules:
--------
- mam_crawler: MAM guide crawling with stealth behavior
- metadata_correction: Google Books → Goodreads metadata enrichment
- series_completion: Series gap discovery and auto-download
- author_completion: Author catalog discovery and auto-download
- top10_discovery: MAM top-10 genre scraping

Usage Example:
--------------
```python
from backend.database import get_db_context
from backend.modules import crawl_mam_guides, correct_all_books

# Crawl MAM guides
with get_db_context() as db:
    result = await crawl_mam_guides(db_session=db)
    print(f"Crawled {result['guides_count']} guides")

# Correct metadata for all books
with get_db_context() as db:
    result = await correct_all_books(db_session=db, limit=100)
    print(f"Updated {result['succeeded']} books")
```
"""

# MAM Crawler module
from backend.modules.mam_crawler import (
    crawl_mam_guides,
    get_crawler_status,
    reset_crawler_state
)

# Metadata Correction module
from backend.modules.metadata_correction import (
    correct_book_metadata,
    correct_all_books
)

# Series Completion module
from backend.modules.series_completion import (
    find_missing_series_books,
    download_missing_series_books,
    import_and_correct_series
)

# Author Completion module
from backend.modules.author_completion import (
    find_missing_author_books,
    download_missing_author_books,
    import_and_correct_authors
)

# Top 10 Discovery module
from backend.modules.top10_discovery import (
    scrape_mam_top10,
    queue_top10_downloads,
    get_available_genres
)

__all__ = [
    # MAM Crawler
    "crawl_mam_guides",
    "get_crawler_status",
    "reset_crawler_state",

    # Metadata Correction
    "correct_book_metadata",
    "correct_all_books",

    # Series Completion
    "find_missing_series_books",
    "download_missing_series_books",
    "import_and_correct_series",

    # Author Completion
    "find_missing_author_books",
    "download_missing_author_books",
    "import_and_correct_authors",

    # Top 10 Discovery
    "scrape_mam_top10",
    "queue_top10_downloads",
    "get_available_genres",
]


# Module metadata
__version__ = "1.0.0"
__author__ = "MAMcrawler Backend Team"
__description__ = "FastAPI-compatible wrappers for MAMcrawler project scripts"
