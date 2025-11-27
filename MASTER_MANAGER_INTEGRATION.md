# Master Manager Integration Guide

## Overview

This guide shows how to integrate the Selenium crawler into `master_audiobook_manager.py` with minimal code changes.

## Changes Required

### 1. Add Import (Line ~40-45)

**Before:**
```python
# Import existing components
from unified_metadata_aggregator import get_metadata
from audiobookshelf_metadata_sync import AudiobookshelfMetadataSync
from stealth_audiobookshelf_crawler import StealthMAMAudiobookshelfCrawler
from audiobook_auto_batch import AutomatedAudiobookBatch
```

**After:**
```python
# Import existing components
from unified_metadata_aggregator import get_metadata
from audiobookshelf_metadata_sync import AudiobookshelfMetadataSync
# from stealth_audiobookshelf_crawler import StealthMAMAudiobookshelfCrawler  # DEPRECATED
from audiobook_auto_batch import AutomatedAudiobookBatch
from selenium_integration import run_selenium_top_search, SeleniumSearchTermGenerator, SeleniumIntegrationConfig
```

### 2. Add Configuration Check (In `__init__`, after line ~56)

**Add:**
```python
        # Check Selenium integration availability
        self.selenium_available = SeleniumIntegrationConfig.validate()
        if self.selenium_available:
            self.logger.info("✓ Selenium integration available - will use for search operations")
        else:
            self.logger.warning("⚠ Selenium integration not configured - searches may fail")
```

### 3. Add New Method for Selenium Search (Line ~472, before `run_top_10_search`)

**Add this new method:**
```python
    async def run_selenium_search_safe(self, search_books: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Safely run Selenium crawler with error handling.

        Args:
            search_books: Optional list of books to search for

        Returns:
            Result dict with search statistics
        """
        try:
            # Generate search terms if not provided
            if not search_books:
                search_books = await self.get_books_for_search()

            if not search_books:
                self.logger.warning("No books to search for")
                return {
                    'success': False,
                    'error': 'No search books provided',
                    'searched': 0,
                    'found': 0,
                    'queued': 0
                }

            # Run Selenium search
            result = await run_selenium_top_search(books=search_books)

            self.stats['search_results'] = result.get('queued', 0)

            return result

        except Exception as e:
            error_msg = f"Selenium search failed: {e}"
            self.logger.error(error_msg)
            self.stats['errors'].append({
                'operation': 'selenium_search',
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })
            return {
                'success': False,
                'error': error_msg,
                'searched': 0,
                'found': 0,
                'queued': 0
            }

    async def get_books_for_search(self) -> List[Dict]:
        """Get list of books to search for (missing books, author discovery, etc.)"""
        books = []

        # Example: Get books marked for manual search
        # In a real implementation, this would check database
        # For now, return empty list (will use missing analysis instead)

        return books
```

### 4. Replace `run_top_10_search` Method (Lines 473-514)

**Before:**
```python
    async def run_top_10_search(self) -> Dict[str, Any]:
        """
        Run top 10 audiobook search using the stealth crawler.
        Returns the most recent/relevant audiobooks found.
        """
        self.logger.info("=" * 70)
        self.logger.info("TOP 10 AUDIOBOOK SEARCH")
        self.logger.info("=" * 70)

        try:
            # Run the stealth audiobookshelf crawler
            crawler = StealthMAMAudiobookshelfCrawler()

            # Run the crawler
            await crawler.run()

            # Collect results from all output files
            search_results = await self.collect_search_results()

            # Select top 10 most recent/relevant
            top_10 = self.select_top_10_audiobooks(search_results)

            # Generate search report
            search_report = await self.generate_search_report(top_10)

            self.stats['search_results'] = len(search_results)

            return {
                'success': True,
                'total_found': len(search_results),
                'top_10': top_10,
                'report': search_report
            }

        except Exception as e:
            self.logger.error(f"Top 10 search failed: {e}")
            self.stats['errors'].append({
                'operation': 'top_10_search',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return {'success': False, 'error': str(e)}
```

**After:**
```python
    async def run_top_10_search(self) -> Dict[str, Any]:
        """
        Run top 10 audiobook search using Selenium crawler.
        Returns the most recent/relevant audiobooks found.
        Integrated with missing book detection for targeted searches.
        """
        self.logger.info("=" * 70)
        self.logger.info("TOP 10 AUDIOBOOK SEARCH (Selenium Crawler)")
        self.logger.info("=" * 70)

        try:
            if not self.selenium_available:
                self.logger.error("Selenium integration not available")
                return {
                    'success': False,
                    'error': 'Selenium not configured',
                    'searched': 0,
                    'found': 0,
                    'queued': 0
                }

            # Option 1: Run with missing book detection results
            # Detect missing books first and search for them
            self.logger.info("Step 1: Detecting missing books...")
            missing_analysis = await self.detect_missing_books()

            if not missing_analysis.get('success'):
                self.logger.warning("Missing book detection failed, running general search instead")
                # Fallback to general search
                result = await self.run_selenium_search_safe()
            else:
                # Option 2: Search for detected missing books
                self.logger.info("Step 2: Searching for missing books with Selenium...")
                result = await run_selenium_top_search(missing_analysis=missing_analysis)

            # Update stats
            self.stats['search_results'] = result.get('queued', 0)

            # Generate search report
            search_report = await self.generate_search_report({
                'searched': result.get('searched', 0),
                'found': result.get('found', 0),
                'queued': result.get('queued', 0),
                'duplicates': result.get('duplicates', 0)
            })

            return {
                'success': result.get('success', False),
                'searched': result.get('searched', 0),
                'found': result.get('found', 0),
                'queued': result.get('queued', 0),
                'duplicates': result.get('duplicates', 0),
                'missing_analysis': missing_analysis,
                'report': search_report
            }

        except Exception as e:
            self.logger.error(f"Top 10 search failed: {e}")
            self.stats['errors'].append({
                'operation': 'top_10_search',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return {
                'success': False,
                'error': str(e),
                'searched': 0,
                'found': 0,
                'queued': 0
            }
```

### 5. Update `generate_search_report` Method (Lines 684-701)

**Before:**
```python
    async def generate_search_report(self, top_10: List[Dict]) -> str:
        """Generate search results report."""
        report_file = self.output_dirs['search_results'] / f"top_10_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        report = f"# Top 10 Audiobook Search Results\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        for i, audiobook in enumerate(top_10, 1):
            report += f"## {i}. {audiobook.get('title', 'Unknown Title')}\n"
            report += f"- **Author:** {audiobook.get('author', 'Unknown')}\n"
            report += f"- **Size:** {audiobook.get('size', 'Unknown')}\n"
            report += f"- **Category:** {audiobook.get('category', 'Unknown')}\n"
            report += f"- **Search Term:** {audiobook.get('search_term', 'Unknown')}\n\n"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        self.logger.info(f"Search report saved: {report_file}")
        return str(report_file)
```

**After:**
```python
    async def generate_search_report(self, search_data: Dict) -> str:
        """Generate search results report."""
        report_file = self.output_dirs['search_results'] / f"selenium_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        report = f"# Selenium Crawler Search Results\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # Handle both old format (list) and new format (dict)
        if isinstance(search_data, list):
            # Old format: list of audiobooks
            for i, audiobook in enumerate(search_data, 1):
                report += f"## {i}. {audiobook.get('title', 'Unknown Title')}\n"
                report += f"- **Author:** {audiobook.get('author', 'Unknown')}\n"
                report += f"- **Size:** {audiobook.get('size', 'Unknown')}\n"
                report += f"- **Category:** {audiobook.get('category', 'Unknown')}\n"
                report += f"- **Search Term:** {audiobook.get('search_term', 'Unknown')}\n\n"
        else:
            # New format: search statistics
            report += f"## Search Statistics\n\n"
            report += f"- **Books Searched:** {search_data.get('searched', 0)}\n"
            report += f"- **Found:** {search_data.get('found', 0)}\n"
            report += f"- **Queued:** {search_data.get('queued', 0)}\n"
            report += f"- **Duplicates:** {search_data.get('duplicates', 0)}\n"

            if search_data.get('found', 0) > 0:
                report += f"\n**Success Rate:** {(search_data.get('queued', 0) / search_data.get('found', 1) * 100):.1f}%\n"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        self.logger.info(f"Search report saved: {report_file}")
        return str(report_file)
```

### 6. Optional: Add Fallback for Old `collect_search_results` (Keep lines 516-532)

The existing method can stay but won't be used:

```python
    async def collect_search_results(self) -> List[Dict]:
        """
        DEPRECATED: Collect results from search output files.
        Kept for backward compatibility. Use Selenium integration instead.
        """
        self.logger.warning("collect_search_results is deprecated. Use Selenium crawler instead.")
        results = []
        search_dir = Path("audiobookshelf_output")

        if not search_dir.exists():
            return results

        for json_file in search_dir.glob("audiobookshelf_*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results.extend(data)
            except Exception as e:
                self.logger.warning(f"Could not read {json_file}: {e}")

        return results
```

## Environment Configuration

Add to your `.env` file:

```bash
# Selenium Crawler Configuration
MAM_USERNAME=your_mam_username
MAM_PASSWORD=your_mam_password

# qBittorrent Configuration
QB_HOST=http://localhost:8080
QB_USERNAME=admin
QB_PASSWORD=your_qbittorrent_password

# Optional: Selenium Options
MAM_SELENIUM_HEADLESS=true
MAM_SELENIUM_TIMEOUT=30
MAM_SELENIUM_DEBUG=false
```

## Testing the Integration

### Test 1: Check Configuration

```bash
python -c "from selenium_integration import SeleniumIntegrationConfig; print(SeleniumIntegrationConfig.validate())"
```

**Expected Output:** `True`

### Test 2: Run Master Manager with Selenium

```bash
python master_audiobook_manager.py --top-search
```

**Expected Output:**
```
======================================================================
TOP 10 AUDIOBOOK SEARCH (Selenium Crawler)
======================================================================
Step 1: Detecting missing books...
...
Step 2: Searching for missing books with Selenium...
...
Selenium search completed: {'total_searched': N, 'found': M, 'queued': M, ...}
```

### Test 3: Full Sync with Selenium

```bash
python master_audiobook_manager.py --full-sync
```

This will:
1. Update metadata
2. Detect missing books
3. Search for them with Selenium
4. Queue to qBittorrent
5. Generate reports

## Rollback Plan

If you need to revert to the old system:

1. Comment out Selenium import:
```python
# from selenium_integration import run_selenium_top_search, ...
```

2. Restore old `run_top_10_search` method

3. Set environment variable to disable Selenium:
```bash
USE_SELENIUM=false
```

## Troubleshooting

### Error: "Configuration validation failed"

**Cause:** Missing environment variables

**Fix:** Ensure all required environment variables are set:
```bash
echo $MAM_USERNAME
echo $QB_HOST
```

### Error: "Selenium crawler initialization failed"

**Cause:** Missing Python packages or WebDriver issues

**Fix:**
```bash
pip install selenium webdriver-manager beautifulsoup4 qbittorrent-api
```

### Error: "No search terms generated"

**Cause:** Missing book detection returned empty results

**Fix:** Ensure Audiobookshelf is running and has books:
```bash
curl -H "Authorization: Bearer $ABS_TOKEN" http://localhost:13378/api/libraries
```

### Slow Performance

**Cause:** JavaScript execution overhead

**Expected:** 5-10 seconds per search

**Optimization:** Batch searches in single browser session (already implemented)

## Integration Verification Checklist

After making changes, verify:

- [ ] Imports compile without errors
- [ ] `SeleniumIntegrationConfig.validate()` returns `True`
- [ ] `--status` flag shows Selenium as available
- [ ] `--top-search` completes without errors
- [ ] Torrents appear in qBittorrent
- [ ] Reports are generated in `search_results/` directory
- [ ] No duplicate queues detected
- [ ] Missing book detection output matches search terms

