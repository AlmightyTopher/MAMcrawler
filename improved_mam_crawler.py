"""
Improved MAM Guides Crawler - Integrating Crawl4AI Best Practices
- Schema-based extraction for efficiency
- Session management for authentication
- Batch processing with arun_many
- Better error handling and logging
"""

import asyncio
import os
import re
import json
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mam_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ImprovedMAMCrawler:
    """Enhanced MAM crawler with crawl4ai best practices."""

    def __init__(self):
        self.username = os.getenv('MAM_USERNAME')
        self.password = os.getenv('MAM_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("MAM_USERNAME and MAM_PASSWORD must be set in .env file")

        self.base_url = "https://www.myanonamouse.net"
        self.session_id = "mam_authenticated_session"
        self.session_cookies = None
        self.is_authenticated = False

        self.output_dir = Path("guides_output")
        self.output_dir.mkdir(exist_ok=True)

        # Browser configuration optimized for MAM
        self.browser_config = BrowserConfig(
            headless=True,
            viewport_width=1920,
            viewport_height=1080,
            verbose=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Guide extraction schema (CSS-based, very efficient)
        self.guide_schema = {
            "name": "guides",
            "baseSelector": "a[href*='/guides/']",
            "fields": [
                {"name": "title", "selector": "self::text", "type": "text"},
                {"name": "url", "selector": "self::attr", "attribute": "href", "type": "text"}
            ]
        }

    async def authenticate(self, crawler: AsyncWebCrawler) -> bool:
        """
        Authenticate using browser automation with JavaScript execution.
        This handles all JavaScript, cookies, and CSRF tokens automatically.
        """
        if self.is_authenticated:
            logger.info("Already authenticated, reusing session")
            return True

        logger.info("Authenticating with MyAnonamouse using browser automation...")

        try:
            login_url = f"{self.base_url}/login.php"

            # JavaScript code to fill and submit the login form
            js_login = f"""
            // Wait for page to load
            await new Promise(resolve => setTimeout(resolve, 2000));

            // Fill in login form
            const emailInput = document.querySelector('input[name="email"]');
            const passwordInput = document.querySelector('input[name="password"]');

            if (emailInput && passwordInput) {{
                emailInput.value = '{self.username}';
                passwordInput.value = '{self.password}';

                // Submit the form
                const submitBtn = document.querySelector('input[type="submit"]');
                if (submitBtn) {{
                    submitBtn.click();
                }} else {{
                    document.querySelector('form').submit();
                }}

                // Wait for redirect/response
                await new Promise(resolve => setTimeout(resolve, 3000));
            }}
            """

            config = CrawlerRunConfig(
                session_id=self.session_id,
                cache_mode=CacheMode.BYPASS,
                js_code=js_login,
                wait_for="css:body",
                page_timeout=60000,  # Longer timeout for login
                screenshot=True  # Take screenshot for debugging
            )

            result = await crawler.arun(url=login_url, config=config)

            if result.success:
                # Check if login was successful
                response_text = result.markdown.lower()

                if "logout" in response_text or "my account" in response_text or "userdetails" in response_text:
                    logger.info("Authentication successful - found user menu")
                    self.is_authenticated = True

                    # Save screenshot for verification
                    if result.screenshot:
                        import base64
                        screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                        with open('mam_login_success.png', 'wb') as f:
                            f.write(screenshot_data)
                        logger.info("Login screenshot saved to mam_login_success.png")

                    return True
                else:
                    logger.error("Authentication failed - login elements not found")

                    # Save debug info
                    with open('mam_login_debug.html', 'w', encoding='utf-8') as f:
                        f.write(result.html if result.html else "No HTML captured")
                    logger.info("Debug HTML saved to mam_login_debug.html")

                    if result.screenshot:
                        import base64
                        screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                        with open('mam_login_failed.png', 'wb') as f:
                            f.write(screenshot_data)
                        logger.info("Failed login screenshot saved to mam_login_failed.png")

                    return False
            else:
                logger.error(f"Browser automation failed: {result.error_message}")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def extract_all_guide_links(self, crawler: AsyncWebCrawler) -> List[Dict[str, str]]:
        """
        Extract all guide links from main /guides page using schema-based extraction.
        This is much more efficient than manual HTML parsing.
        """
        guides_url = f"{self.base_url}/guides/"
        logger.info(f"Extracting guide links from: {guides_url}")

        # Use schema-based extraction (no LLM needed)
        extraction_strategy = JsonCssExtractionStrategy(
            schema=self.guide_schema,
            verbose=True
        )

        crawler_config = CrawlerRunConfig(
            session_id=self.session_id,
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction_strategy,
            wait_for="css:body",
            page_timeout=30000,
            remove_overlay_elements=True
        )

        try:
            result = await crawler.arun(url=guides_url, config=crawler_config)

            if not result.success:
                logger.error(f"Failed to crawl guides page: {result.error_message}")
                return []

            # Parse extracted JSON or HTML
            if result.extracted_content:
                try:
                    data = json.loads(result.extracted_content)
                    # Handle both dict and list responses
                    if isinstance(data, list):
                        guides = data
                    else:
                        guides = data.get("guides", [])
                except json.JSONDecodeError:
                    guides = []
                    logger.warning("Failed to parse extracted content as JSON")

                # If extraction failed or returned empty, fall back to HTML parsing
                if not guides and result.html:
                    logger.info("Falling back to HTML parsing...")
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(result.html, 'lxml')
                    guides_raw = soup.find_all('a', href=lambda h: h and '/guides/' in h)

                    guides = []
                    for link in guides_raw:
                        guides.append({
                            'url': link.get('href', ''),
                            'title': link.get_text(strip=True) or 'Untitled'
                        })

                # Process and deduplicate
                guide_links = []
                seen_urls = set()

                for guide in guides:
                    url = guide.get('url', '') if isinstance(guide, dict) else guide
                    title = guide.get('title', 'Untitled') if isinstance(guide, dict) else 'Untitled'

                    # Make URL absolute
                    if url.startswith('/'):
                        url = f"{self.base_url}{url}"

                    # Skip duplicates and non-guide links
                    if url in seen_urls or not '/guides/' in url or url == guides_url:
                        continue

                    seen_urls.add(url)

                    guide_links.append({
                        'url': url,
                        'title': title,
                        'category': self.extract_category_from_url(url)
                    })

                logger.info(f"Extracted {len(guide_links)} unique guide links")
                return guide_links
            else:
                logger.warning("No content extracted from guides page")
                return []

        except Exception as e:
            logger.error(f"Error extracting guide links: {e}")
            import traceback
            traceback.print_exc()
            return []

    def extract_category_from_url(self, url: str) -> str:
        """Extract category from URL path."""
        path_parts = url.rstrip('/').split('/')
        if len(path_parts) >= 2:
            category = path_parts[-2] if path_parts[-1] else path_parts[-2]
            if category != 'guides':
                return category.replace('-', ' ').replace('_', ' ').title()
        return "General"

    async def crawl_guides_batch(self, crawler: AsyncWebCrawler, guide_links: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Crawl multiple guides efficiently using batch processing.
        Uses crawl4ai's arun_many for concurrent crawling.
        """
        if not guide_links:
            logger.warning("No guide links to crawl")
            return []

        logger.info(f"Starting batch crawl of {len(guide_links)} guides")

        # Prepare URLs for batch crawling
        urls = [guide['url'] for guide in guide_links]

        # Configure crawler for batch processing
        crawler_config = CrawlerRunConfig(
            session_id=self.session_id,
            cache_mode=CacheMode.BYPASS,
            wait_for="css:body",
            page_timeout=30000,
            remove_overlay_elements=True,
            screenshot=False  # Disable for batch efficiency
        )

        try:
            # Use arun_many for efficient concurrent crawling (respecting rate limits)
            results = await crawler.arun_many(
                urls=urls,
                config=crawler_config,
                max_concurrent=3  # Conservative to respect MAM
            )

            processed_guides = []

            for i, result in enumerate(results):
                guide_info = guide_links[i]

                if result.success:
                    guide_data = {
                        'success': True,
                        'url': result.url,
                        'title': guide_info['title'],
                        'category': guide_info['category'],
                        'content': result.markdown,
                        'metadata': result.metadata,
                        'links': result.links,
                        'crawled_at': datetime.now().isoformat()
                    }
                    processed_guides.append(guide_data)
                    logger.info(f"Successfully crawled: {guide_info['title']}")
                else:
                    logger.warning(f"Failed to crawl: {guide_info['title']} - {result.error_message}")
                    processed_guides.append({
                        'success': False,
                        'url': result.url,
                        'title': guide_info['title'],
                        'error': result.error_message
                    })

            logger.info(f"Batch crawl complete: {len(processed_guides)} guides processed")
            return processed_guides

        except Exception as e:
            logger.error(f"Batch crawl error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def sanitize_filename(self, title: str) -> str:
        """Convert title to safe filename."""
        filename = re.sub(r'[<>:"/\\|?*]', '', title)
        filename = re.sub(r'\s+', '_', filename)
        return filename[:100]

    def save_guide_to_file(self, guide_data: Dict[str, Any]):
        """Save guide to individual markdown file."""
        if not guide_data.get('success'):
            return

        filename = self.sanitize_filename(guide_data['title']) + ".md"
        filepath = self.output_dir / filename

        content = f"# {guide_data['title']}\n\n"
        content += f"**URL:** {guide_data['url']}\n\n"
        content += f"**Category:** {guide_data.get('category', 'General')}\n\n"

        if guide_data.get('metadata'):
            meta = guide_data['metadata']
            if meta.get('title'):
                content += f"**Page Title:** {meta['title']}\n\n"
            if meta.get('description'):
                content += f"**Description:** {meta['description']}\n\n"

        content += f"**Crawled:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "---\n\n"

        # Add related links
        if guide_data.get('links'):
            internal_links = guide_data['links'].get('internal', [])
            if internal_links:
                guide_links = [link for link in internal_links if '/guides/' in link]
                if guide_links:
                    content += "## Related Guides\n\n"
                    for link in guide_links[:20]:  # Limit to 20
                        content += f"- {link}\n"
                    content += "\n---\n\n"

        content += "## Content\n\n"
        content += guide_data.get('content', 'No content extracted')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Saved: {filename}")

    def generate_summary_report(self, guides: List[Dict[str, Any]]):
        """Generate summary report of crawled guides."""
        report_file = self.output_dir / "CRAWL_SUMMARY.md"

        successful = [g for g in guides if g.get('success')]
        failed = [g for g in guides if not g.get('success')]

        content = f"# MAM Guides Crawl Summary\n\n"
        content += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"**Total Guides:** {len(guides)}\n\n"
        content += f"**Successful:** {len(successful)}\n\n"
        content += f"**Failed:** {len(failed)}\n\n"
        content += "---\n\n"

        # Organize by category
        categories = {}
        for guide in successful:
            cat = guide.get('category', 'General')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(guide)

        content += "## Guides by Category\n\n"
        for category in sorted(categories.keys()):
            guides_list = categories[category]
            content += f"### {category} ({len(guides_list)})\n\n"
            for guide in sorted(guides_list, key=lambda x: x['title']):
                filename = self.sanitize_filename(guide['title']) + ".md"
                content += f"- [{guide['title']}]({filename})\n"
            content += "\n"

        if failed:
            content += "## Failed Crawls\n\n"
            for guide in failed:
                content += f"- {guide['title']} ({guide['url']})\n"
                content += f"  Error: {guide.get('error', 'Unknown')}\n"
            content += "\n"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Summary report saved to {report_file}")

    async def run(self):
        """Main execution method."""
        logger.info("="*60)
        logger.info("Starting Improved MAM Guides Crawler")
        logger.info("="*60)

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            # Step 1: Authenticate
            if not await self.authenticate(crawler):
                logger.error("Authentication failed. Exiting.")
                return

            # Step 2: Extract all guide links
            guide_links = await self.extract_all_guide_links(crawler)

            if not guide_links:
                logger.error("No guide links found. Exiting.")
                return

            logger.info(f"Found {len(guide_links)} guides to crawl")

            # Step 3: Batch crawl all guides
            guides_data = await self.crawl_guides_batch(crawler, guide_links)

            # Step 4: Save individual guide files
            for guide_data in guides_data:
                if guide_data.get('success'):
                    self.save_guide_to_file(guide_data)

            # Step 5: Generate summary report
            self.generate_summary_report(guides_data)

            logger.info("="*60)
            logger.info(f"Crawl complete! {len([g for g in guides_data if g.get('success')])} guides saved to {self.output_dir}")
            logger.info("="*60)


async def main():
    """Entry point."""
    try:
        crawler = ImprovedMAMCrawler()
        await crawler.run()
    except KeyboardInterrupt:
        logger.info("Crawl interrupted by user")
    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
