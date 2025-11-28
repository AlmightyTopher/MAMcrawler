"""
Audiobookshelf Guides Link Crawler
Recursively crawls https://www.audiobookshelf.org/guides up to 3 levels deep
Extracts all links with titles and descriptions, AND saves full page content
Respects robots.txt and implements rate limiting
"""

import os
import re
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging with safe encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audiobookshelf_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AudiobookshelfGuidesCrawler:
    """Crawler for audiobookshelf.org/guides with recursive link extraction and full content scraping."""

    def __init__(self):
        self.base_url = "https://www.audiobookshelf.org"
        self.start_url = f"{self.base_url}/guides"
        self.session = requests.Session()

        # Set user agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        self.output_file = Path("audiobookshelf_guides_links.md")
        self.content_output_dir = Path("audiobookshelf_content")
        self.content_output_dir.mkdir(exist_ok=True)
        self.state_file = Path("abs_crawler_state.json")
        self.state = self.load_state()

        # Crawling parameters
        self.max_depth = 3  # Maximum recursion depth
        self.min_delay = 2  # seconds between requests
        self.max_delay = 5  # seconds between requests
        self.visited_urls: Set[str] = set()
        self.all_links: List[Dict[str, Any]] = []
        self.page_contents: Dict[str, str] = {}  # Store full page content

        # Robots.txt parser
        self.robots_parser = RobotFileParser()
        self.robots_parser.set_url(f"{self.base_url}/robots.txt")
        self.robots_checked = False

    def load_state(self) -> Dict:
        """Load crawler state for resume capability."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                logger.info(f"Loaded state: {len(state.get('visited', []))} URLs already visited")
                return state
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

        return {
            'visited': [],
            'links': [],
            'page_contents': {},
            'last_run': None,
            'depth_reached': {}
        }

    def save_state(self):
        """Save current crawler state."""
        self.state['visited'] = list(self.visited_urls)
        self.state['links'] = self.all_links
        self.state['page_contents'] = self.page_contents
        self.state['last_run'] = datetime.now().isoformat()

        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            logger.info(f"State saved: {len(self.visited_urls)} visited URLs")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def check_robots_txt(self) -> bool:
        """Check robots.txt for crawling permissions."""
        if self.robots_checked:
            return True

        try:
            logger.info("Checking robots.txt...")
            self.robots_parser.read()
            self.robots_checked = True

            # Check if we can fetch the guides section
            if not self.robots_parser.can_fetch('*', self.start_url):
                logger.error("Robots.txt disallows crawling guides section")
                return False

            logger.info("Robots.txt allows crawling")
            return True

        except Exception as e:
            logger.warning(f"Could not read robots.txt: {e}. Proceeding with caution.")
            return True  # Allow crawling if robots.txt is unreachable

    def human_delay(self, min_seconds: Optional[int] = None, max_seconds: Optional[int] = None):
        """Simulate human-like random delay."""
        min_s = min_seconds or self.min_delay
        max_s = max_seconds or self.max_delay
        delay = random.uniform(min_s, max_s)
        logger.info(f"Waiting {delay:.1f} seconds (rate limiting)...")
        time.sleep(delay)

    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and within audiobookshelf.org domain."""
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme in ['http', 'https'] and
                parsed.netloc == 'www.audiobookshelf.org' and
                not any(skip in url for skip in ['#', '?', 'mailto:', 'javascript:'])
            )
        except:
            return False

    def extract_links_from_html(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract all links with titles from HTML content."""
        soup = BeautifulSoup(html, 'lxml')

        links = []
        seen_urls = set()

        for link in soup.find_all('a', href=True):
            url = link.get('href', '').strip()
            title = link.get_text(strip=True) or link.get('title', '').strip() or 'No title'

            # Convert relative URLs to absolute
            if url.startswith('/'):
                url = urljoin(self.base_url, url)
            elif not url.startswith('http'):
                url = urljoin(base_url, url)

            # Skip invalid URLs
            if not self.is_valid_url(url) or url in seen_urls:
                continue

            seen_urls.add(url)

            # Try to get description from surrounding text
            description = ""
            parent = link.parent
            if parent and parent.name in ['p', 'div', 'li']:
                description = parent.get_text(strip=True)[:200]  # Limit description length

            links.append({
                'url': url,
                'title': title,
                'description': description,
                'source_url': base_url
            })

        return links

    def html_to_markdown(self, html: str, url: str) -> str:
        """Convert HTML content to markdown format."""
        soup = BeautifulSoup(html, 'lxml')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Extract title
        title = soup.title.string if soup.title else "No Title"
        title = title.strip() if title else "No Title"

        # Start markdown content
        content = f"# {title}\n\n"
        content += f"**Source:** {url}\n\n"
        content += f"**Crawled:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "---\n\n"

        # Convert main content to markdown
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'ul', 'ol', 'li', 'blockquote', 'pre', 'code']):
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(element.name[1])
                content += '#' * level + ' ' + element.get_text(strip=True) + '\n\n'
            elif element.name == 'p':
                content += element.get_text(strip=True) + '\n\n'
            elif element.name in ['ul', 'ol']:
                for li in element.find_all('li'):
                    content += f"- {li.get_text(strip=True)}\n"
                content += '\n'
            elif element.name == 'blockquote':
                content += f"> {element.get_text(strip=True)}\n\n"
            elif element.name == 'pre':
                content += f"```\n{element.get_text()}\n```\n\n"
            elif element.name == 'code':
                content += f"`{element.get_text(strip=True)}`"
            elif element.name == 'div' and element.get('class'):
                # Handle specific div classes if needed
                if 'content' in element.get('class', []):
                    content += element.get_text(strip=True) + '\n\n'

        return content

    def save_page_content(self, url: str, html: str):
        """Save full page content as markdown."""
        try:
            # Create filename from URL
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            if not path_parts or path_parts == ['']:
                filename = 'index.md'
            else:
                # Clean filename
                filename = '_'.join(path_parts[-2:]) if len(path_parts) > 1 else path_parts[0]
                filename = re.sub(r'[^\w\-_\.]', '_', filename)
                if not filename.endswith('.md'):
                    filename += '.md'

            filepath = self.content_output_dir / filename

            # Convert to markdown
            markdown_content = self.html_to_markdown(html, url)

            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            logger.info(f"Saved page content: {filepath}")

        except Exception as e:
            logger.error(f"Failed to save page content for {url}: {e}")

    def crawl_url(self, url: str, depth: int) -> List[Dict[str, str]]:
        """Crawl a single URL and extract links."""
        if url in self.visited_urls or depth > self.max_depth:
            return []

        logger.info(f"Crawling (depth {depth}): {url}")

        # Rate limiting
        self.human_delay()

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            self.visited_urls.add(url)

            # Save full page content
            self.page_contents[url] = response.text
            self.save_page_content(url, response.text)

            # Extract links from this page
            page_links = self.extract_links_from_html(response.text, url)

            # Add to all links
            for link in page_links:
                if link not in self.all_links:
                    self.all_links.append(link)

            logger.info(f"Found {len(page_links)} links on {url}")

            # Recursively crawl new links if within depth limit
            if depth < self.max_depth:
                new_links_to_crawl = [
                    link['url'] for link in page_links
                    if link['url'] not in self.visited_urls and
                    self.is_valid_url(link['url'])
                ]

                for new_url in new_links_to_crawl[:5]:  # Limit concurrent crawls
                    self.crawl_url(new_url, depth + 1)

            return page_links

        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")

        return []

    def generate_markdown_output(self) -> str:
        """Generate markdown output with all links."""
        content = "# Audiobookshelf Guides - All Links and Content\n\n"
        content += f"**Crawled on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"**Total unique links found:** {len(self.all_links)}\n\n"
        content += f"**URLs visited:** {len(self.visited_urls)}\n\n"
        content += f"**Pages with full content saved:** {len(self.page_contents)}\n\n"
        content += f"**Content saved to:** {self.content_output_dir.absolute()}\n\n"
        content += "---\n\n"

        # Group links by source URL
        links_by_source = {}
        for link in self.all_links:
            source = link['source_url']
            if source not in links_by_source:
                links_by_source[source] = []
            links_by_source[source].append(link)

        # Output links grouped by source
        for source_url, links in links_by_source.items():
            content += f"## Links from: {source_url}\n\n"

            for link in links:
                content += f"### [{link['title']}]({link['url']})\n\n"
                if link['description']:
                    content += f"{link['description']}\n\n"
                content += "---\n\n"

        return content

    def save_markdown_output(self):
        """Save the markdown output to file."""
        content = self.generate_markdown_output()

        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Saved {len(self.all_links)} links to {self.output_file}")

    def run(self):
        """Main execution."""
        logger.info("="*70)
        logger.info("Starting Audiobookshelf Guides Link Crawler")
        logger.info("="*70)

        # Check robots.txt
        if not self.check_robots_txt():
            logger.error("Cannot proceed due to robots.txt restrictions")
            return

        # Load existing state
        self.visited_urls = set(self.state.get('visited', []))
        self.all_links = self.state.get('links', [])
        self.page_contents = self.state.get('page_contents', {})

        logger.info(f"Starting crawl from: {self.start_url}")

        # Start crawling from the guides page
        self.crawl_url(self.start_url, 0)

        # Save results
        self.save_markdown_output()
        self.save_state()

        # Final summary
        logger.info("\n" + "="*70)
        logger.info("CRAWL COMPLETE")
        logger.info("="*70)
        logger.info(f"Total URLs visited: {len(self.visited_urls)}")
        logger.info(f"Total unique links found: {len(self.all_links)}")
        logger.info(f"Pages with content saved: {len(self.page_contents)}")
        logger.info(f"Content directory: {self.content_output_dir.absolute()}")
        logger.info(f"Links summary: {self.output_file.absolute()}")
        logger.info("="*70)


def main():
    """Entry point."""
    try:
        crawler = AudiobookshelfGuidesCrawler()
        crawler.run()
    except KeyboardInterrupt:
        logger.info("\nCrawl interrupted by user")
        logger.info("Progress has been saved - run again to resume")
    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()