"""
Enhanced MAM Guides Crawler
Extracts all guides from myanonamouse.net/guides and creates individual MD files for each guide.
"""

import asyncio
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import urlparse, urljoin

from mam_crawler import MAMPassiveCrawler
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import CrawlerRunConfig
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedGuideCrawler:
    """Enhanced crawler for comprehensive MAM guides extraction."""

    def __init__(self):
        self.crawler = MAMPassiveCrawler()
        self.output_dir = Path("guides_output")
        self.output_dir.mkdir(exist_ok=True)
        self.crawled_guides = []

    def sanitize_filename(self, title: str) -> str:
        """Convert guide title to valid filename."""
        # Remove special characters and replace spaces with underscores
        filename = re.sub(r'[<>:"/\\|?*]', '', title)
        filename = re.sub(r'\s+', '_', filename)
        # Limit length
        filename = filename[:100]
        return filename

    async def extract_all_guide_links(self) -> List[Dict[str, str]]:
        """
        Extract all guide links from the main /guides page.

        Returns:
            List of dicts with 'url', 'title', and 'category' keys
        """
        guides_url = f"{self.crawler.base_url}/guides/"
        logger.info(f"Crawling main guides page: {guides_url}")

        # First, ensure we're authenticated
        if not await self.crawler._ensure_authenticated():
            logger.error("Failed to authenticate")
            return []

        await self.crawler._rate_limit()

        try:
            async with AsyncWebCrawler() as web_crawler:
                import random
                user_agent = random.choice(self.crawler.user_agents)

                config = CrawlerRunConfig(
                    verbose=True,
                    user_agent=user_agent
                )

                result = await web_crawler.arun(url=guides_url, config=config)

                if not result.success:
                    logger.error(f"Failed to crawl guides page: {result.error if hasattr(result, 'error') else 'Unknown error'}")
                    return []

                # Parse the HTML to extract guide links
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.html, 'lxml')

                guide_links = []

                # Find all links that contain '/guides/' in the href
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/guides/' in href and href != '/guides/':
                        # Get full URL
                        if href.startswith('/'):
                            full_url = f"{self.crawler.base_url}{href}"
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = urljoin(guides_url, href)

                        # Extract title from link text
                        title = link.get_text(strip=True) or "Untitled Guide"

                        # Try to determine category from URL or parent elements
                        category = self.extract_category(link, href)

                        guide_links.append({
                            'url': full_url,
                            'title': title,
                            'category': category
                        })

                # Remove duplicates based on URL
                unique_guides = {guide['url']: guide for guide in guide_links}
                guide_links = list(unique_guides.values())

                logger.info(f"Found {len(guide_links)} unique guide links")

                # Save the main guides index page as well
                await self.save_main_index(result, guide_links)

                return guide_links

        except Exception as e:
            logger.error(f"Error extracting guide links: {e}")
            import traceback
            traceback.print_exc()
            return []

    def extract_category(self, link_element, href: str) -> str:
        """Extract category from link context or URL."""
        # Try to find parent heading or section
        parent = link_element.find_parent(['div', 'section', 'article'])
        if parent:
            heading = parent.find(['h1', 'h2', 'h3', 'h4'])
            if heading:
                return heading.get_text(strip=True)

        # Try to extract from URL path
        path_parts = href.split('/')
        if len(path_parts) > 2:
            category = path_parts[-2] if path_parts[-1] else path_parts[-2]
            return category.replace('-', ' ').replace('_', ' ').title()

        return "General"

    async def save_main_index(self, result, guide_links: List[Dict[str, str]]):
        """Save the main guides index page."""
        index_file = self.output_dir / "00_GUIDES_INDEX.md"

        content = f"# MyAnonamouse Guides Index\n\n"
        content += f"**Crawled:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"**Total Guides Found:** {len(guide_links)}\n\n"
        content += "---\n\n"

        # Organize by category
        categories = {}
        for guide in guide_links:
            cat = guide['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(guide)

        content += "## Guide Categories\n\n"
        for category, guides in sorted(categories.items()):
            content += f"### {category} ({len(guides)} guides)\n\n"
            for guide in guides:
                filename = self.sanitize_filename(guide['title'])
                content += f"- [{guide['title']}]({filename}.md) - {guide['url']}\n"
            content += "\n"

        content += "---\n\n"
        content += "## Full Page Content\n\n"
        content += result.markdown if result.markdown else "No content extracted"

        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Saved main index to {index_file}")

    async def crawl_individual_guide(self, guide_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Crawl an individual guide page and extract all content.

        Args:
            guide_info: Dict with 'url', 'title', 'category' keys

        Returns:
            Dict with extracted guide data
        """
        url = guide_info['url']
        title = guide_info['title']

        logger.info(f"Crawling guide: {title}")

        await self.crawler._rate_limit()

        try:
            async with AsyncWebCrawler() as web_crawler:
                import random
                user_agent = random.choice(self.crawler.user_agents)

                config = CrawlerRunConfig(
                    verbose=False,
                    user_agent=user_agent
                )

                result = await web_crawler.arun(url=url, config=config)

                if not result.success:
                    error_msg = result.error if hasattr(result, 'error') else 'Unknown error'
                    logger.error(f"Failed to crawl guide '{title}': {error_msg}")
                    return {
                        'success': False,
                        'url': url,
                        'title': title,
                        'error': error_msg
                    }

                # Parse HTML for structured extraction
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.html, 'lxml')

                # Extract metadata
                description = self.extract_description(soup)
                author = self.extract_author(soup)
                last_updated = self.extract_date(soup)
                tags = self.extract_tags(soup)

                # Extract sub-links within this guide
                sub_links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/guides/' in href and href != url:
                        sub_title = link.get_text(strip=True)
                        if href.startswith('/'):
                            full_href = f"{self.crawler.base_url}{href}"
                        elif href.startswith('http'):
                            full_href = href
                        else:
                            full_href = urljoin(url, href)

                        sub_links.append({
                            'url': full_href,
                            'title': sub_title
                        })

                return {
                    'success': True,
                    'url': url,
                    'title': title,
                    'category': guide_info['category'],
                    'description': description,
                    'author': author,
                    'last_updated': last_updated,
                    'tags': tags,
                    'content': result.markdown,
                    'html_content': result.html,
                    'sub_links': sub_links,
                    'crawled_at': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Error crawling guide '{title}': {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'url': url,
                'title': title,
                'error': str(e)
            }

    def extract_description(self, soup) -> str:
        """Extract guide description from HTML."""
        # Try common description selectors
        for selector in ['.description', '.intro', '.summary', 'meta[name="description"]']:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == 'meta':
                    return elem.get('content', '')
                return elem.get_text(strip=True)
        return ""

    def extract_author(self, soup) -> str:
        """Extract author from HTML."""
        for selector in ['.author', '.byline', '.posted-by', 'meta[name="author"]']:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == 'meta':
                    return elem.get('content', '')
                return elem.get_text(strip=True)
        return ""

    def extract_date(self, soup) -> str:
        """Extract last updated date from HTML."""
        for selector in ['.date', '.updated', '.last-modified', 'time']:
            elem = soup.select_one(selector)
            if elem:
                # Check for datetime attribute
                if elem.has_attr('datetime'):
                    return elem['datetime']
                return elem.get_text(strip=True)
        return ""

    def extract_tags(self, soup) -> str:
        """Extract tags/categories from HTML."""
        tags = []
        for selector in ['.tags a', '.categories a', '.tag']:
            elems = soup.select(selector)
            for elem in elems:
                tag_text = elem.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)

        return ', '.join(tags) if tags else ""

    def save_guide_to_file(self, guide_data: Dict[str, Any]):
        """Save guide data to individual MD file."""
        if not guide_data.get('success'):
            logger.warning(f"Skipping failed guide: {guide_data.get('title', 'Unknown')}")
            return

        filename = self.sanitize_filename(guide_data['title']) + ".md"
        filepath = self.output_dir / filename

        # Build markdown content
        content = f"# {guide_data['title']}\n\n"
        content += f"**URL:** {guide_data['url']}\n\n"
        content += f"**Category:** {guide_data.get('category', 'General')}\n\n"

        if guide_data.get('description'):
            content += f"**Description:** {guide_data['description']}\n\n"

        if guide_data.get('author'):
            content += f"**Author:** {guide_data['author']}\n\n"

        if guide_data.get('last_updated'):
            content += f"**Last Updated:** {guide_data['last_updated']}\n\n"

        if guide_data.get('tags'):
            content += f"**Tags:** {guide_data['tags']}\n\n"

        content += f"**Crawled:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "---\n\n"

        # Add sub-links if found
        if guide_data.get('sub_links'):
            content += "## Related Guides\n\n"
            for sub_link in guide_data['sub_links']:
                content += f"- [{sub_link['title']}]({sub_link['url']})\n"
            content += "\n---\n\n"

        # Add main content
        content += "## Content\n\n"
        content += guide_data.get('content', 'No content extracted')

        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Saved guide to {filepath}")
        self.crawled_guides.append({
            'title': guide_data['title'],
            'filename': filename,
            'url': guide_data['url'],
            'category': guide_data.get('category', 'General')
        })

    async def crawl_all_guides(self):
        """Main method to crawl all guides and create individual files."""
        logger.info("Starting comprehensive MAM guides extraction...")

        # Step 1: Extract all guide links from main page
        guide_links = await self.extract_all_guide_links()

        if not guide_links:
            logger.error("No guide links found. Exiting.")
            return

        logger.info(f"Found {len(guide_links)} guides to crawl")

        # Step 2: Crawl each guide individually
        for i, guide_info in enumerate(guide_links, 1):
            logger.info(f"Processing guide {i}/{len(guide_links)}: {guide_info['title']}")

            guide_data = await self.crawl_individual_guide(guide_info)
            self.save_guide_to_file(guide_data)

            # Extra delay between guides to be respectful
            await asyncio.sleep(2)

        # Step 3: Generate summary report
        self.generate_summary_report()

        logger.info(f"✓ Crawling complete! {len(self.crawled_guides)} guides saved to {self.output_dir}")

    def generate_summary_report(self):
        """Generate a summary report of all crawled guides."""
        report_file = self.output_dir / "CRAWL_SUMMARY.md"

        content = f"# MAM Guides Crawl Summary\n\n"
        content += f"**Crawl Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"**Total Guides Crawled:** {len(self.crawled_guides)}\n\n"
        content += f"**Output Directory:** `{self.output_dir.absolute()}`\n\n"
        content += "---\n\n"

        # Organize by category
        categories = {}
        for guide in self.crawled_guides:
            cat = guide['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(guide)

        content += "## Guides by Category\n\n"
        for category, guides in sorted(categories.items()):
            content += f"### {category} ({len(guides)} guides)\n\n"
            for guide in sorted(guides, key=lambda x: x['title']):
                content += f"- [{guide['title']}]({guide['filename']})\n"
                content += f"  - URL: {guide['url']}\n"
            content += "\n"

        content += "---\n\n"
        content += "## Files Created\n\n"
        for guide in sorted(self.crawled_guides, key=lambda x: x['filename']):
            content += f"- `{guide['filename']}`\n"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Summary report saved to {report_file}")


async def main():
    """Main entry point."""
    try:
        crawler = EnhancedGuideCrawler()
        await crawler.crawl_all_guides()
    except KeyboardInterrupt:
        logger.info("Crawl interrupted by user")
    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
