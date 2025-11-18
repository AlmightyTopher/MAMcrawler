"""
Audiobook Catalog Crawler
Crawls https://mango-mushroom-0d3dde80f.azurestaticapps.net/
Extracts genres, timespans, and audiobook data for querying.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audiobook_catalog.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AudiobookCatalogCrawler:
    """Crawler for audiobook catalog website with dynamic filtering."""

    def __init__(self):
        self.base_url = "https://mango-mushroom-0d3dde80f.azurestaticapps.net/"
        self.cache_dir = Path("catalog_cache")
        self.cache_dir.mkdir(exist_ok=True)

        self.catalog_file = self.cache_dir / "audiobook_catalog.json"
        self.genres_file = self.cache_dir / "genres.json"
        self.timespans_file = self.cache_dir / "timespans.json"

    def create_browser_config(self) -> BrowserConfig:
        """Create browser configuration for JavaScript-heavy site."""
        return BrowserConfig(
            headless=True,
            viewport_width=1920,
            viewport_height=1080,
            verbose=True,
            java_script_enabled=True,
            ignore_https_errors=False
        )

    async def navigate_to_audiobooks(self, crawler: AsyncWebCrawler) -> Dict[str, Any]:
        """
        Navigate to the audiobooks section of the site.

        Returns:
            Result data including HTML and extracted information
        """
        logger.info("🔍 Loading audiobook catalog website...")

        # JavaScript to wait for React app to load and navigate to audiobooks
        js_navigate = """
        // Wait for React app to fully load
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Look for audiobooks link/button
        const audiobooksLink = Array.from(document.querySelectorAll('a, button, div[role="button"]'))
            .find(el => el.textContent.toLowerCase().includes('audiobook'));

        if (audiobooksLink) {
            audiobooksLink.click();
            await new Promise(resolve => setTimeout(resolve, 2000));
        }

        // Wait for content to load
        await new Promise(resolve => setTimeout(resolve, 3000));
        """

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=js_navigate,
            wait_for="css:body",
            page_timeout=60000,
            screenshot=True
        )

        try:
            result = await crawler.arun(url=self.base_url, config=config)

            if result.success:
                logger.info("✅ Successfully loaded audiobooks section")

                # Save screenshot for debugging
                if result.screenshot:
                    import base64
                    screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                    with open(self.cache_dir / 'audiobooks_page.png', 'wb') as f:
                        f.write(screenshot_data)
                    logger.info("📸 Screenshot saved to catalog_cache/audiobooks_page.png")

                return {
                    'success': True,
                    'html': result.html,
                    'markdown': result.markdown,
                    'links': result.links
                }
            else:
                logger.error(f"❌ Failed to load page: {result.error_message}")
                return {'success': False, 'error': result.error_message}

        except Exception as e:
            logger.error(f"❌ Navigation error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    async def extract_filters(self, crawler: AsyncWebCrawler) -> Dict[str, Any]:
        """
        Extract available genre and timespan filters from the page.

        Returns:
            Dictionary containing genres and timespans
        """
        logger.info("📋 Extracting genre and timespan filters...")

        # JavaScript to extract filter options
        js_extract_filters = """
        // Wait for page to load
        await new Promise(resolve => setTimeout(resolve, 3000));

        const filters = {
            genres: [],
            timespans: []
        };

        // Try to find genre selectors (dropdowns, buttons, checkboxes, etc.)
        const genreElements = document.querySelectorAll('[class*="genre" i], [id*="genre" i], select[name*="genre" i], option[value*="genre" i]');
        genreElements.forEach(el => {
            const text = el.textContent.trim();
            const value = el.value || el.getAttribute('data-value') || text;
            if (text && text.length > 0 && text.length < 100) {
                filters.genres.push({ label: text, value: value });
            }
        });

        // Try to find timespan/date range selectors
        const timespanElements = document.querySelectorAll('[class*="time" i], [class*="date" i], [class*="year" i], select[name*="time" i], select[name*="date" i]');
        timespanElements.forEach(el => {
            const text = el.textContent.trim();
            const value = el.value || el.getAttribute('data-value') || text;
            if (text && text.length > 0 && text.length < 100) {
                filters.timespans.push({ label: text, value: value });
            }
        });

        // If no specific filters found, try to get all selects and their options
        if (filters.genres.length === 0 && filters.timespans.length === 0) {
            const allSelects = document.querySelectorAll('select');
            allSelects.forEach((select, index) => {
                const options = Array.from(select.options).map(opt => ({
                    label: opt.textContent.trim(),
                    value: opt.value
                }));

                if (index === 0) {
                    filters.genres = options;
                } else {
                    filters.timespans = options;
                }
            });
        }

        // Return as JSON string for extraction
        return JSON.stringify(filters);
        """

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=js_extract_filters,
            wait_for="css:body",
            page_timeout=60000
        )

        try:
            result = await crawler.arun(url=self.base_url, config=config)

            if result.success:
                # Try to extract filters from page structure
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.html, 'lxml')

                filters = {
                    'genres': [],
                    'timespans': []
                }

                # Look for select elements
                selects = soup.find_all('select')
                for i, select in enumerate(selects):
                    options = []
                    for option in select.find_all('option'):
                        if option.get_text(strip=True):
                            options.append({
                                'label': option.get_text(strip=True),
                                'value': option.get('value', option.get_text(strip=True))
                            })

                    # First select is likely genres, second is timespans
                    if i == 0 and options:
                        filters['genres'] = options
                    elif i == 1 and options:
                        filters['timespans'] = options

                # Save filters to cache
                if filters['genres'] or filters['timespans']:
                    with open(self.genres_file, 'w') as f:
                        json.dump(filters['genres'], f, indent=2)
                    with open(self.timespans_file, 'w') as f:
                        json.dump(filters['timespans'], f, indent=2)

                    logger.info(f"✅ Found {len(filters['genres'])} genres and {len(filters['timespans'])} timespans")
                    return filters
                else:
                    logger.warning("⚠️  No filters found, returning page content for manual inspection")
                    return {
                        'genres': [],
                        'timespans': [],
                        'html_preview': result.html[:1000]
                    }

        except Exception as e:
            logger.error(f"❌ Filter extraction error: {e}")
            import traceback
            traceback.print_exc()
            return {'genres': [], 'timespans': [], 'error': str(e)}

    async def query_audiobooks(self, crawler: AsyncWebCrawler, genre: str, timespan: str) -> List[Dict[str, Any]]:
        """
        Query audiobooks by genre and timespan.

        Args:
            genre: Selected genre value
            timespan: Selected timespan value

        Returns:
            List of audiobook entries
        """
        logger.info(f"🔍 Querying audiobooks: Genre={genre}, Timespan={timespan}")

        # JavaScript to select filters and extract results
        js_query = f"""
        // Wait for page to load
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Try to find and set genre selector
        const genreSelect = document.querySelector('select:first-of-type') ||
                           document.querySelector('[name*="genre" i]') ||
                           document.querySelector('[id*="genre" i]');

        if (genreSelect && genreSelect.tagName === 'SELECT') {{
            genreSelect.value = '{genre}';
            genreSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
            await new Promise(resolve => setTimeout(resolve, 1000));
        }}

        // Try to find and set timespan selector
        const timespanSelect = document.querySelectorAll('select')[1] ||
                              document.querySelector('[name*="time" i]') ||
                              document.querySelector('[name*="date" i]');

        if (timespanSelect && timespanSelect.tagName === 'SELECT') {{
            timespanSelect.value = '{timespan}';
            timespanSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
            await new Promise(resolve => setTimeout(resolve, 1000));
        }}

        // Click search/submit button if present
        const submitBtn = document.querySelector('button[type="submit"]') ||
                         document.querySelector('button:contains("Search")') ||
                         document.querySelector('button:contains("Go")');

        if (submitBtn) {{
            submitBtn.click();
            await new Promise(resolve => setTimeout(resolve, 2000));
        }}

        // Wait for results to load
        await new Promise(resolve => setTimeout(resolve, 3000));
        """

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=js_query,
            wait_for="css:body",
            page_timeout=60000,
            screenshot=True
        )

        try:
            result = await crawler.arun(url=self.base_url, config=config)

            if result.success:
                # Save screenshot of results
                if result.screenshot:
                    import base64
                    screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                    filename = f"results_{genre}_{timespan}.png".replace('/', '_').replace('\\', '_')
                    with open(self.cache_dir / filename, 'wb') as f:
                        f.write(screenshot_data)
                    logger.info(f"📸 Results screenshot saved")

                # Extract audiobook entries from the page
                audiobooks = await self._extract_audiobooks_from_html(result.html, result.markdown)

                logger.info(f"✅ Found {len(audiobooks)} audiobooks")
                return audiobooks
            else:
                logger.error(f"❌ Query failed: {result.error_message}")
                return []

        except Exception as e:
            logger.error(f"❌ Query error: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _extract_audiobooks_from_html(self, html: str, markdown: str) -> List[Dict[str, Any]]:
        """
        Extract audiobook data from HTML results page.

        Args:
            html: Raw HTML content
            markdown: Markdown version of content

        Returns:
            List of audiobook dictionaries
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')

        audiobooks = []

        # Look for common patterns in audiobook listings
        # This will need to be adjusted based on actual site structure

        # Try table rows
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:  # Likely has title, author, etc.
                audiobook = {
                    'title': cells[0].get_text(strip=True) if cells[0] else '',
                    'author': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                    'info': cells[2].get_text(strip=True) if len(cells) > 2 else ''
                }

                # Look for download/torrent links
                links = row.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    if 'torrent' in href or 'magnet:' in href or 'download' in href:
                        audiobook['link'] = href

                if audiobook['title']:
                    audiobooks.append(audiobook)

        # Try list items
        for item in soup.find_all(['li', 'div'], class_=lambda c: c and ('result' in c.lower() or 'item' in c.lower() or 'book' in c.lower())):
            title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'a'])
            if title_elem:
                audiobook = {
                    'title': title_elem.get_text(strip=True),
                    'html_content': str(item)[:500]  # Store snippet for debugging
                }

                # Look for links
                for link in item.find_all('a'):
                    href = link.get('href', '')
                    if href:
                        audiobook['link'] = href

                audiobooks.append(audiobook)

        # If no structured data found, save raw content for manual inspection
        if not audiobooks:
            logger.warning("⚠️  No audiobooks extracted from structured elements")
            logger.info("Saving raw content for inspection...")

            with open(self.cache_dir / 'raw_results.html', 'w', encoding='utf-8') as f:
                f.write(html)
            with open(self.cache_dir / 'raw_results.md', 'w', encoding='utf-8') as f:
                f.write(markdown)

        return audiobooks

    async def discover_site_structure(self) -> Dict[str, Any]:
        """
        Initial discovery run to understand the site structure.
        This should be run once to map out the interface.

        Returns:
            Site structure information
        """
        logger.info("="*70)
        logger.info("🔍 DISCOVERING SITE STRUCTURE")
        logger.info("="*70)

        browser_config = self.create_browser_config()

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Step 1: Navigate to audiobooks
            nav_result = await self.navigate_to_audiobooks(crawler)

            if not nav_result.get('success'):
                logger.error("❌ Failed to navigate to audiobooks section")
                return nav_result

            # Step 2: Extract filters
            filters = await self.extract_filters(crawler)

            return {
                'success': True,
                'filters': filters,
                'navigation': nav_result
            }


async def main():
    """Entry point for discovery."""
    crawler = AudiobookCatalogCrawler()

    # Run discovery to map site structure
    result = await crawler.discover_site_structure()

    if result.get('success'):
        logger.info("\n" + "="*70)
        logger.info("✅ DISCOVERY COMPLETE")
        logger.info("="*70)
        logger.info(f"Genres found: {len(result['filters'].get('genres', []))}")
        logger.info(f"Timespans found: {len(result['filters'].get('timespans', []))}")
        logger.info("\nNext steps:")
        logger.info("1. Review catalog_cache/audiobooks_page.png")
        logger.info("2. Check catalog_cache/genres.json and timespans.json")
        logger.info("3. Run audiobook_query.py to interactively query the catalog")
    else:
        logger.error("❌ Discovery failed")
        logger.error(f"Error: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
