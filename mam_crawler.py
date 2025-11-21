"""
Passive Crawling Service for MyAnonamouse.net
Uses Crawl4AI for stealthy, passive web crawling that mimics normal user behavior.
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time
import random
import re

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ratelimit import limits, sleep_and_retry
import markdown
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Shared Stealth Library
from mamcrawler.stealth import StealthCrawler

class MAMPassiveCrawler(StealthCrawler):
    """
    Passive crawler for MyAnonamouse.net that respects site terms and mimics normal user behavior.
    """

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        # Initialize StealthCrawler with specific state file
        super().__init__(state_file="mam_crawler_state.json")

        # Use environment variables for credentials
        self.username = username or os.getenv('MAM_USERNAME')
        self.password = password or os.getenv('MAM_PASSWORD')

        # Allow demo mode without credentials
        demo_mode = os.getenv('MAM_DEMO_MODE', 'false').lower() == 'true'
        if not demo_mode and (not self.username or not self.password):
            raise ValueError("MAM credentials not provided. Set MAM_USERNAME and MAM_PASSWORD environment variables, or set MAM_DEMO_MODE=true for demo mode.")

        self.base_url = "https://www.myanonamouse.net"
        self.session_cookies = None
        self.last_login = None
        self.login_expiry = timedelta(hours=2)  # MAM sessions typically last 2 hours

        # Rate limiting to mimic human behavior
        # (Inherited from StealthCrawler: self.min_delay, self.max_delay)
        self.last_request = datetime.now()

        # User agent rotation
        # (Inherited from StealthCrawler: self.user_agents)

        # Crawling restrictions - only publicly viewable content
        self.allowed_paths = [
            "/",  # homepage
            "/t/",  # torrent pages (public)
            "/tor/browse.php",  # browse page
            "/tor/search.php",  # search results
            "/guides/",  # guides section
            "/f/",  # forum sections (public)
        ]

    async def _rate_limit(self):
        """Implement rate limiting to avoid detection."""
        # Use shared human_delay
        await self.human_delay(self.min_delay, self.max_delay)
        self.last_request = datetime.now()

    async def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid authenticated session."""
        now = datetime.now()

        # First, try to use cookies from environment if available
        env_uid = os.getenv('uid')
        env_mam_id = os.getenv('mam_id')
        if env_uid and env_mam_id and not self.session_cookies:
            logger.info("Using session cookies from environment")
            self.session_cookies = {
                'uid': env_uid,
                'mam_id': env_mam_id
            }
            self.last_login = now
            return True

        # Check if we need to login
        if (self.last_login is None or
            now - self.last_login > self.login_expiry or
            self.session_cookies is None):

            logger.info("Authenticating with MyAnonamouse.net")
            success = await self._login()
            if not success:
                logger.error("Failed to authenticate")
                return False

        return True

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def _login(self) -> bool:
        """Perform login using provided credentials with retry logic."""
        try:
            import aiohttp

            login_url = f"{self.base_url}/takelogin.php"

            # MAM login requires form submission with username/password
            login_data = {
                "username": self.username,
                "password": self.password,
                "login": "Login"  # MAM login button value
            }

            # Use aiohttp for proper POST authentication
            user_agent = self.get_user_agent()
            headers = {
                'User-Agent': user_agent,
                'Referer': f"{self.base_url}/login.php",
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            async with aiohttp.ClientSession() as session:
                # First visit login page to get session cookies
                async with session.get(f"{self.base_url}/login.php", headers=headers) as resp:
                    await resp.text()

                # Submit login form with POST
                async with session.post(login_url, data=login_data, headers=headers, allow_redirects=True) as resp:
                    response_text = await resp.text()
                    response_status = resp.status

                    # Save response for debugging (only in debug mode to avoid exposing session tokens)
                    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
                    if debug_mode:
                        with open('mam_login_response.html', 'w', encoding='utf-8') as f:
                            f.write(response_text)
                        logger.debug("Login response saved to mam_login_response.html for debugging")

                    logger.info(f"Login response status: {response_status}")
                    logger.info(f"Response length: {len(response_text)} bytes")

                    # Check if login was successful
                    # Login successful if: status is 200-299 AND response doesn't contain "login failed" error
                    is_success = (200 <= response_status < 300) and "login failed" not in response_text.lower()

                    if is_success:
                        logger.info("Login successful - received 2xx response without login failed error")
                        self.last_login = datetime.now()

                        # Store session cookies
                        self.session_cookies = {cookie.key: cookie.value for cookie in session.cookie_jar}
                        logger.info(f"Stored {len(self.session_cookies)} session cookies")
                        return True
                    else:
                        # Check for common error messages
                        if "invalid" in response_text.lower() or "incorrect" in response_text.lower():
                            logger.error("Login failed - invalid credentials")
                        elif "captcha" in response_text.lower():
                            logger.error("Login failed - CAPTCHA required")
                        elif "banned" in response_text.lower() or "disabled" in response_text.lower():
                            logger.error("Login failed - account may be banned or disabled")
                        else:
                            logger.error("Login failed - credentials may be invalid or site structure changed")

                        if debug_mode:
                            logger.info("Response saved to mam_login_response.html for debugging")
                        return False

        except Exception as e:
            logger.error(f"Login failed: {e}")
            import traceback
            traceback.print_exc()
            raise  # Re-raise to trigger retry

    def _is_allowed_path(self, url: str) -> bool:
        """Check if the URL path is allowed for passive crawling."""
        from urllib.parse import urlparse
        parsed = urlparse(url)

        # Must be on the correct domain
        if parsed.netloc != "www.myanonamouse.net":
            return False

        # Check against allowed paths
        path = parsed.path
        for allowed in self.allowed_paths:
            # Handle homepage as exact match only
            if allowed == "/" and path == "/":
                return True
            # For other paths, check prefix but not for "/"
            elif allowed != "/" and path.startswith(allowed):
                return True

        return False

    async def crawl_page(self, url: str, extraction_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Crawl a single page passively with user agent rotation and rate limiting.

        Args:
            url: The URL to crawl
            extraction_config: Optional extraction configuration

        Returns:
            Dict containing crawled data
        """
        if not self._is_allowed_path(url):
            return {
                "success": False,
                "error": "URL not allowed for passive crawling",
                "url": url
            }

        await self._rate_limit()

        # Ensure authentication if needed
        if not await self._ensure_authenticated():
            return {
                "success": False,
                "error": "Authentication failed",
                "url": url
            }

        try:
            # Build CrawlerRunConfig using shared stealth config
            # We create a browser config first to get the viewport/UA
            browser_config = self.create_browser_config(headless=True)
            
            config = CrawlerRunConfig(
                verbose=False,
                user_agent=browser_config.user_agent,
                js_code=self.create_stealth_js(), # Inject stealth JS
                wait_for="css:body"
            )

            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url, config=config)

                # Anonymize the data
                anonymized_data = self._anonymize_data(result)

                return {
                    "success": result.success,
                    "url": result.url,
                    "title": result.title,
                    "content_length": len(result.markdown) if result.markdown else 0,
                    "crawled_at": datetime.now().isoformat(),
                    "data": anonymized_data
                }

        except Exception as e:
            logger.error(f"Crawling failed for {url}: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    def _anonymize_data(self, result) -> Dict[str, Any]:
        """
        Anonymize crawled data to remove sensitive information.

        Args:
            result: Crawl4AI result object

        Returns:
            Anonymized data dict
        """
        # Remove any potential user-specific information
        anonymized = {
            "title": result.title,
            "url": result.url,
            "content_type": "public_page",
            "crawl_timestamp": datetime.now().isoformat()
        }

        # Only include markdown content if it's from allowed public pages
        if result.markdown and self._is_allowed_path(result.url):
            # Remove any user mentions, emails, or personal data
            content = result.markdown
            # Basic anonymization - remove potential email patterns
            import re
            content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', content)
            # Remove potential usernames
            content = re.sub(r'\buser[_-]\w+\b', '[USER]', content, flags=re.IGNORECASE)

            anonymized["content"] = content[:5000]  # Limit content length

        return anonymized

    def trigger_ingestion(self):
        """Trigger RAG ingestion pipeline."""
        logger.info("Triggering RAG ingestion...")
        try:
            import subprocess
            import sys
            subprocess.Popen([sys.executable, "ingest.py"])
            logger.info("RAG ingestion started in background")
        except Exception as e:
            logger.error(f"Failed to trigger ingestion: {e}")

    async def crawl_public_pages(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Crawl multiple public pages with enhanced rate limiting.

        Args:
            urls: List of URLs to crawl

        Returns:
            List of crawl results
        """
        results = []

        for url in urls:
            logger.info(f"Crawling: {url}")
            result = await self.crawl_page(url)
            results.append(result)

            # Add random delay between requests (already handled by rate_limit, but extra safety)
            await asyncio.sleep(random.uniform(1, 3))

        return results

    async def crawl_guides_section(self) -> List[Dict[str, Any]]:
        """
        Crawl the /guides/ section of MAM to extract structured guide data with recursive sub-link discovery.

        Returns:
            List of guide data dictionaries
        """
        guides_url = f"{self.base_url}/guides/"
        result = await self.crawl_page(guides_url)

        if not result["success"]:
            return [result]

        guides_data = []

        # First, get the main guides page to find all guide links
        extraction_config = {
            "type": "css_selector",
            "params": {
                "name": "GuidesListExtractor",
                "fields": [
                    {"name": "guide_links", "selector": "a[href*='/guides/']", "type": "attribute", "attribute": "href"},
                    {"name": "guide_titles", "selector": "a[href*='/guides/']", "type": "text"}
                ]
            }
        }

        list_result = await self.crawl_page(guides_url, extraction_config)

        if list_result.get("success") and list_result.get("data"):
            guide_links = list_result["data"].get("guide_links", [])
            guide_titles = list_result["data"].get("guide_titles", [])

            # Crawl individual guide pages recursively
            visited_urls = set()
            await self._crawl_guides_recursively(guide_links, guide_titles, guides_data, visited_urls, max_depth=3)

        # If no individual guides found, return the main page data
        if not guides_data:
            guides_data = [list_result]

        return guides_data

    async def _crawl_guides_recursively(self, links: List[str], titles: List[str], guides_data: List[Dict[str, Any]],
                                       visited_urls: set, max_depth: int = 3, current_depth: int = 0) -> None:
        """
        Recursively crawl guide pages and their sub-links.

        Args:
            links: List of guide URLs to crawl
            titles: Corresponding titles
            guides_data: List to append results to
            visited_urls: Set of already visited URLs
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth
        """
        if current_depth >= max_depth:
            return

        for i, link in enumerate(links):
            if link.startswith('/'):
                full_url = f"{self.base_url}{link}"
            elif link.startswith('http'):
                full_url = link
            else:
                continue

            if full_url in visited_urls:
                continue

            visited_urls.add(full_url)

            logger.info(f"Crawling guide (depth {current_depth}): {titles[i] if i < len(titles) else 'Unknown'}")

            # Extract detailed guide content
            guide_extraction_config = {
                "type": "css_selector",
                "params": {
                    "name": "GuideDetailExtractor",
                    "fields": [
                        {"name": "title", "selector": "h1, h2, .guide-title", "type": "text"},
                        {"name": "description", "selector": ".guide-description, .description, .intro", "type": "text"},
                        {"name": "author", "selector": ".author, .guide-author, .byline", "type": "text"},
                        {"name": "timestamp", "selector": ".timestamp, .date, .published", "type": "text"},
                        {"name": "content", "selector": ".guide-content, .content, article", "type": "text"},
                        {"name": "tags", "selector": ".tags, .categories", "type": "text"},
                        {"name": "sub_links", "selector": "a[href*='/guides/']", "type": "attribute", "attribute": "href"},
                        {"name": "sub_titles", "selector": "a[href*='/guides/']", "type": "text"}
                    ]
                }
            }

            guide_result = await self.crawl_page(full_url, guide_extraction_config)
            guides_data.append(guide_result)

            # Extract sub-links and crawl them recursively
            if guide_result.get("success") and guide_result.get("data"):
                sub_links = guide_result["data"].get("sub_links", [])
                sub_titles = guide_result["data"].get("sub_titles", [])

                if sub_links:
                    await self._crawl_guides_recursively(sub_links, sub_titles, guides_data, visited_urls,
                                                       max_depth, current_depth + 1)

            # Rate limiting between guide pages
            await asyncio.sleep(random.uniform(2, 5))

    async def crawl_qbittorrent_settings(self) -> List[Dict[str, Any]]:
        """
        Crawl the /f section to extract qBittorrent settings and configuration parameters from recent threads.

        Returns:
            List of qBittorrent settings data
        """
        qbittorrent_data = []

        # Define forum sections to search
        forum_sections = [
            f"{self.base_url}/f/",  # Main forum
            f"{self.base_url}/f/2/",  # General discussion
            f"{self.base_url}/f/3/",  # Technical support
            f"{self.base_url}/f/4/",  # Site feedback
        ]

        # Keywords for qBittorrent-related content
        qb_keywords = [
            "qbittorrent", "qbt", "qbittorrent settings", "qbittorrent config",
            "qbittorrent setup", "qbittorrent optimization", "qbittorrent performance",
            "qbittorrent troubleshooting", "qbittorrent maintenance", "qbittorrent best practices"
        ]

        visited_threads = set()

        for forum_url in forum_sections:
            logger.info(f"Searching forum section: {forum_url}")

            # Get forum page to find threads
            forum_result = await self.crawl_page(forum_url)
            if not forum_result["success"]:
                continue

            # Extract thread links and metadata
            thread_extraction_config = {
                "type": "css_selector",
                "params": {
                    "name": "ForumThreadExtractor",
                    "fields": [
                        {"name": "thread_links", "selector": "a[href*='/f/'][href*='/']", "type": "attribute", "attribute": "href"},
                        {"name": "thread_titles", "selector": "a[href*='/f/'][href*='/']", "type": "text"},
                        {"name": "thread_dates", "selector": ".date, .timestamp, .post-date", "type": "text"},
                        {"name": "thread_authors", "selector": ".author, .poster, .username", "type": "text"}
                    ]
                }
            }

            threads_result = await self.crawl_page(forum_url, thread_extraction_config)

            if threads_result.get("success") and threads_result.get("data"):
                thread_links = threads_result["data"].get("thread_links", [])
                thread_titles = threads_result["data"].get("thread_titles", [])
                thread_dates = threads_result["data"].get("thread_dates", [])
                thread_authors = threads_result["data"].get("thread_authors", [])

                # Filter threads by qBittorrent keywords and date (2021-present)
                filtered_threads = []
                for i, title in enumerate(thread_titles):
                    title_lower = title.lower() if title else ""
                    if any(keyword in title_lower for keyword in qb_keywords):
                        # Check date if available
                        date_str = thread_dates[i] if i < len(thread_dates) else ""
                        if self._is_recent_post(date_str):
                            filtered_threads.append(i)

                logger.info(f"Found {len(filtered_threads)} qBittorrent-related threads in {forum_url}")

                # Crawl filtered threads (limit to 10 per section for passive behavior)
                for idx in filtered_threads[:10]:
                    link = thread_links[idx] if idx < len(thread_links) else None
                    if not link:
                        continue

                    if link.startswith('/'):
                        full_url = f"{self.base_url}{link}"
                    elif link.startswith('http'):
                        full_url = link
                    else:
                        continue

                    if full_url in visited_threads:
                        continue

                    visited_threads.add(full_url)

                    title = thread_titles[idx] if idx < len(thread_titles) else "Unknown"
                    logger.info(f"Crawling qBittorrent thread: {title}")

                    # Extract thread content and settings information
                    thread_extraction_config = {
                        "type": "css_selector",
                        "params": {
                            "name": "QbittorrentThreadExtractor",
                            "fields": [
                                {"name": "title", "selector": "h1, .thread-title, .topic-title", "type": "text"},
                                {"name": "content", "selector": ".post-content, .message, .content, .post-body", "type": "text"},
                                {"name": "author", "selector": ".author, .poster, .username", "type": "text"},
                                {"name": "date", "selector": ".date, .timestamp, .post-date", "type": "text"},
                                {"name": "settings_code", "selector": "code, pre, .code-block, .highlight", "type": "text"},
                                {"name": "attachments", "selector": ".attachment, .file, .download", "type": "text"},
                                {"name": "replies", "selector": ".reply, .post-reply", "type": "text"}
                            ]
                        }
                    }

                    thread_result = await self.crawl_page(full_url, thread_extraction_config)
                    qbittorrent_data.append(thread_result)

                    # Rate limiting between threads
                    await asyncio.sleep(random.uniform(3, 8))

        # If no specific threads found, return forum overview
        if not qbittorrent_data:
            qbittorrent_data = [forum_result]

        return qbittorrent_data

    def _is_recent_post(self, date_str: str) -> bool:
        """
        Check if a post date is from 2021 or later.

        Args:
            date_str: Date string from the forum

        Returns:
            True if post is recent enough
        """
        if not date_str:
            return True  # Include if no date available

        try:
            # Try to parse various date formats
            # Common formats: "2023-01-15", "Jan 15, 2023", "15 Jan 2023", etc.
            from dateutil import parser
            post_date = parser.parse(date_str, fuzzy=True)

            # Check if post is from 2021 or later
            cutoff_date = datetime(2021, 1, 1)
            return post_date >= cutoff_date

        except Exception:
            # If date parsing fails, include the post
            return True

    async def search_and_crawl(self, search_term: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Search for content and crawl resulting pages passively.

        Args:
            search_term: Term to search for
            max_pages: Maximum number of pages to crawl

        Returns:
            List of crawl results
        """
        # Construct search URL (public search)
        search_url = f"{self.base_url}/tor/search.php?search={search_term}&cat=0"

        # First crawl the search results page
        search_result = await self.crawl_page(search_url)

        if not search_result["success"]:
            return [search_result]

        # Extract torrent links from search results
        # This is a simplified example - actual extraction would need proper CSS selectors
        torrent_urls = []

        # For now, return just the search page result
        # In a real implementation, you'd parse the HTML to find torrent links
        logger.warning("Search result parsing not fully implemented - returning search page only")

        return [search_result]


class MAMDataProcessor:
    """
    Processes and outputs crawled MAM data in structured Markdown format.
    """

    def __init__(self):
        self.crawl_timestamp = datetime.now().isoformat()

    def process_guides_data(self, guides_data: List[Dict[str, Any]]) -> str:
        """Process guides data into Markdown format with enhanced structure."""
        markdown_output = f"# MAM Guides\n\nCrawl Timestamp: {self.crawl_timestamp}\n\n"
        markdown_output += "## Overview\n\n"
        markdown_output += "This section contains comprehensive guides from MyAnonamouse.net covering various categories including Basics, Clients, Connectivity, Conversions, InAudible, Legacy, Misc, Optimization, Site, and Uploading.\n\n"

        # Organize guides by categories
        categories = {
            "Basics": [],
            "Clients": [],
            "Connectivity": [],
            "Conversions": [],
            "InAudible": [],
            "Legacy": [],
            "Misc": [],
            "Optimization": [],
            "Site": [],
            "Uploading": []
        }

        successful_guides = 0
        for guide in guides_data:
            if guide.get("success") and guide.get("data"):
                data = guide["data"]
                title = data.get('title', 'Unknown Title')
                if title and title != 'Unknown Title':  # Only include guides with actual titles
                    successful_guides += 1

                    # Try to categorize the guide based on title/URL
                    category = self._categorize_guide(title, guide.get('url', ''))
                    categories[category].append((guide, data))

        # Generate categorized output
        for cat_name, cat_guides in categories.items():
            if cat_guides:
                markdown_output += f"## {cat_name}\n\n"
                for guide, data in cat_guides:
                    title = data.get('title', 'Unknown Title')
                    markdown_output += f"### {title}\n\n"
                    markdown_output += f"- **Description**: {data.get('description', 'N/A')}\n"
                    markdown_output += f"- **Author**: {data.get('author', 'N/A')}\n"
                    markdown_output += f"- **Timestamp**: {data.get('timestamp', 'N/A')}\n"
                    markdown_output += f"- **Tags**: {data.get('tags', 'N/A')}\n"
                    markdown_output += f"- **Source URL**: {guide.get('url', 'N/A')}\n"
                    markdown_output += f"- **Crawl Date**: {guide.get('crawled_at', 'N/A')}\n\n"

                    if data.get('content'):
                        # Clean up content - remove excessive whitespace
                        content = data['content'].strip()
                        if len(content) > 100:  # Only include substantial content
                            markdown_output += f"#### Content\n\n{content}\n\n"
                        
                        # Add summary if content is long
                        if len(content) > 1000:
                            summary = self._generate_summary(content)
                            markdown_output += f"#### Summary\n\n{summary}\n\n"

                    markdown_output += "---\n\n"

        if successful_guides == 0:
            markdown_output += "No guide content was successfully extracted.\n\n"
        else:
            markdown_output += f"**Total Guides Extracted**: {successful_guides}\n\n"

        return markdown_output

    def _categorize_guide(self, title: str, url: str) -> str:
        """Categorize a guide based on its title and URL."""
        title_lower = title.lower()
        url_lower = url.lower()

        # Check for category keywords in title/URL
        if any(word in title_lower or word in url_lower for word in ['basic', 'beginner', 'getting started']):
            return "Basics"
        elif any(word in title_lower or word in url_lower for word in ['client', 'software', 'application']):
            return "Clients"
        elif any(word in title_lower or word in url_lower for word in ['connect', 'network', 'vpn', 'proxy']):
            return "Connectivity"
        elif any(word in title_lower or word in url_lower for word in ['convert', 'format', 'encode']):
            return "Conversions"
        elif any(word in title_lower or word in url_lower for word in ['inaudible', 'audiobook']):
            return "InAudible"
        elif any(word in title_lower or word in url_lower for word in ['legacy', 'old', 'deprecated']):
            return "Legacy"
        elif any(word in title_lower or word in url_lower for word in ['optim', 'performance', 'speed', 'tune']):
            return "Optimization"
        elif any(word in title_lower or word in url_lower for word in ['site', 'website', 'forum', 'account']):
            return "Site"
        elif any(word in title_lower or word in url_lower for word in ['upload', 'torrent', 'seed']):
            return "Uploading"
        else:
            return "Misc"

    def _generate_summary(self, content: str) -> str:
        """Generate a brief summary of guide content."""
        # Simple summary generation - take first few sentences
        sentences = content.split('.')
        summary_sentences = sentences[:3]  # First 3 sentences
        summary = '. '.join(summary_sentences)
        if len(summary) > 300:
            summary = summary[:300] + "..."
        return summary.strip()

    def process_qbittorrent_data(self, qb_data: List[Dict[str, Any]]) -> str:
        """Process qBittorrent settings data into Markdown format with enhanced structure."""
        markdown_output = f"# qBittorrent Settings & Configurations\n\nCrawl Timestamp: {self.crawl_timestamp}\n\n"
        markdown_output += "## Overview\n\n"
        markdown_output += "This section contains qBittorrent-related discussions and configurations from MyAnonamouse.net forums (2021-present). Topics include setup, configuration, maintenance, system optimization, troubleshooting, settings guides, performance tuning, and related best practices.\n\n"

        # Organize threads by categories
        categories = {
            "Setup & Installation": [],
            "Configuration & Settings": [],
            "Performance & Optimization": [],
            "Troubleshooting": [],
            "Maintenance & Best Practices": [],
            "General Discussion": []
        }

        successful_threads = 0
        for thread in qb_data:
            if thread.get("success") and thread.get("data"):
                data = thread["data"]
                title = data.get('title', 'Unknown Thread')
                if title and title != 'Unknown Thread':  # Only include threads with actual titles
                    successful_threads += 1

                    # Categorize the thread
                    category = self._categorize_qbittorrent_thread(title, data.get('content', ''))
                    categories[category].append((thread, data))

        # Generate categorized output
        for cat_name, cat_threads in categories.items():
            if cat_threads:
                markdown_output += f"## {cat_name}\n\n"
                for thread, data in cat_threads:
                    title = data.get('title', 'Unknown Thread')
                    markdown_output += f"### {title}\n\n"
                    markdown_output += f"- **Author**: {data.get('author', 'N/A')}\n"
                    markdown_output += f"- **Date**: {data.get('date', 'N/A')}\n"
                    markdown_output += f"- **Source URL**: {thread.get('url', 'N/A')}\n"
                    markdown_output += f"- **Crawl Date**: {thread.get('crawled_at', 'N/A')}\n\n"

                    # Include settings code blocks if found
                    if data.get('settings_code'):
                        settings_code = data['settings_code'].strip()
                        if settings_code:
                            markdown_output += f"#### Configuration Code\n\n```ini\n{settings_code}\n```\n\n"

                    # Include main content
                    if data.get('content'):
                        content = data['content'].strip()
                        if len(content) > 50:  # Only include substantial content
                            # Clean and format content
                            formatted_content = self._format_thread_content(content)
                            markdown_output += f"#### Thread Content\n\n{formatted_content}\n\n"

                    # Include attachments info
                    if data.get('attachments'):
                        attachments = data['attachments'].strip()
                        if attachments:
                            markdown_output += f"#### Attachments\n\n{attachments}\n\n"

                    # Add summary for long threads
                    if data.get('content') and len(data['content']) > 500:
                        summary = self._generate_thread_summary(data['content'])
                        markdown_output += f"#### Summary\n\n{summary}\n\n"

                    markdown_output += "---\n\n"

        if successful_threads == 0:
            markdown_output += "No qBittorrent configuration content was successfully extracted.\n\n"
        else:
            markdown_output += f"**Total qBittorrent Threads Extracted**: {successful_threads}\n\n"

        return markdown_output

    def _categorize_qbittorrent_thread(self, title: str, content: str) -> str:
        """Categorize a qBittorrent thread based on title and content."""
        title_lower = title.lower()
        content_lower = content.lower() if content else ""

        if any(word in title_lower or word in content_lower for word in ['setup', 'install', 'getting started', 'first time']):
            return "Setup & Installation"
        elif any(word in title_lower or word in content_lower for word in ['config', 'setting', 'option', 'preference']):
            return "Configuration & Settings"
        elif any(word in title_lower or word in content_lower for word in ['performance', 'speed', 'optimize', 'tuning', 'fast']):
            return "Performance & Optimization"
        elif any(word in title_lower or word in content_lower for word in ['problem', 'error', 'issue', 'fix', 'trouble']):
            return "Troubleshooting"
        elif any(word in title_lower or word in content_lower for word in ['maintenance', 'best practice', 'recommend', 'advice']):
            return "Maintenance & Best Practices"
        else:
            return "General Discussion"

    def _format_thread_content(self, content: str) -> str:
        """Format thread content for better readability."""
        # Clean up excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Remove excessive newlines
        content = content.strip()

        # Limit content length for readability
        if len(content) > 2000:
            content = content[:2000] + "...\n\n*[Content truncated for brevity]*"

        return content

    def _generate_thread_summary(self, content: str) -> str:
        """Generate a brief summary of thread content."""
        # Extract key points from the content
        sentences = re.split(r'[.!?]+', content)
        key_sentences = []

        # Look for sentences containing qBittorrent-specific terms
        qb_terms = ['qbittorrent', 'setting', 'config', 'performance', 'optimization', 'troubleshoot', 'fix', 'recommend']

        for sentence in sentences[:10]:  # Check first 10 sentences
            sentence_lower = sentence.lower().strip()
            if any(term in sentence_lower for term in qb_terms) and len(sentence.strip()) > 20:
                key_sentences.append(sentence.strip())

        if key_sentences:
            summary = ' '.join(key_sentences[:3])  # Take up to 3 key sentences
            if len(summary) > 300:
                summary = summary[:300] + "..."
            return summary
        else:
            # Fallback: take first meaningful sentence
            for sentence in sentences:
                if len(sentence.strip()) > 30:
                    return sentence.strip()[:300] + "..." if len(sentence.strip()) > 300 else sentence.strip()

        return "Discussion about qBittorrent configuration and usage."

    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate crawled data for completeness."""
        required_fields = ["success", "url", "crawled_at"]
        return all(field in data for field in required_fields) and data["success"]

    def save_markdown_output(self, guides_md: str, qb_md: str, filename: str = "mam_crawl_output.md"):
        """Save processed data to Markdown file."""
        full_output = f"{guides_md}\n\n{qb_md}"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(full_output)
        logger.info(f"Markdown output saved to {filename}")


async def main():
    """Main entry point for the enhanced MAM crawling service."""

    # Check for demo mode (no credentials required)
    demo_mode = os.getenv('MAM_DEMO_MODE', 'false').lower() == 'true'

    if demo_mode:
        logger.info("Running in demo mode - simulating crawl results")
        # Initialize data processor
        processor = MAMDataProcessor()

        # Create comprehensive sample data for demonstration
        sample_guides_data = [
            {
                "success": True,
                "url": "https://www.myanonamouse.net/guides/basics",
                "title": "Getting Started with MyAnonamouse",
                "crawled_at": datetime.now().isoformat(),
                "data": {
                    "title": "Getting Started with MyAnonamouse",
                    "description": "A comprehensive guide for new users covering account setup, rules, and basic usage",
                    "author": "MAM Staff",
                    "timestamp": "2023-01-15",
                    "content": "Welcome to MyAnonamouse! This guide will help you get started with our private tracker. First, you'll need to create an account and understand our rules. The site focuses on high-quality audiobooks and requires proper seeding ratios. Make sure to read the FAQ section thoroughly before downloading.",
                    "tags": "basics, beginners, getting-started, account-setup"
                }
            },
            {
                "success": True,
                "url": "https://www.myanonamouse.net/guides/clients",
                "title": "Recommended Torrent Clients",
                "crawled_at": datetime.now().isoformat(),
                "data": {
                    "title": "Recommended Torrent Clients",
                    "description": "Guide to choosing and configuring torrent clients for optimal MAM experience",
                    "author": "TechSupport",
                    "timestamp": "2023-03-10",
                    "content": "For the best experience on MyAnonamouse, we recommend using qBittorrent or Deluge. These clients support the advanced features needed for our high-quality torrents. Avoid using outdated clients that may not handle large files properly.",
                    "tags": "clients, software, torrent-clients, recommendations"
                }
            },
            {
                "success": True,
                "url": "https://www.myanonamouse.net/guides/optimization",
                "title": "System Optimization Guide",
                "crawled_at": datetime.now().isoformat(),
                "data": {
                    "title": "System Optimization Guide",
                    "description": "Tips for optimizing your system for better torrent performance and seeding",
                    "author": "PerformanceGuru",
                    "timestamp": "2023-05-22",
                    "content": "To get the most out of MyAnonamouse, optimize your system settings. Ensure you have proper bandwidth allocation, disable unnecessary background processes, and configure your firewall correctly. Regular maintenance like disk defragmentation can significantly improve performance.",
                    "tags": "optimization, performance, system-tuning, maintenance"
                }
            }
        ]

        sample_qb_data = [
            {
                "success": True,
                "url": "https://www.myanonamouse.net/f/123/qbittorrent-settings-guide",
                "title": "qBittorrent Settings for MAM",
                "crawled_at": datetime.now().isoformat(),
                "data": {
                    "title": "qBittorrent Settings for MAM",
                    "author": "TorrentMaster",
                    "date": "2023-06-20",
                    "content": "Here are the recommended qBittorrent settings for optimal performance on MyAnonamouse. These settings are tuned for high-quality audiobooks and ensure proper seeding ratios. Key settings include connection limits, queue management, and bandwidth allocation.",
                    "settings_code": "[Preferences]\nqueueing/max_active_downloads=3\nqueueing/max_active_torrents=6\nconnection/global_max_num_connections=500\nconnection/global_max_upload_slots=20\nspeed/limit_upload_alt=0\nspeed/limit_upload=0\nspeed/limit_download=0"
                }
            },
            {
                "success": True,
                "url": "https://www.myanonamouse.net/f/456/qbittorrent-troubleshooting",
                "title": "qBittorrent Connection Issues",
                "crawled_at": datetime.now().isoformat(),
                "data": {
                    "title": "qBittorrent Connection Issues",
                    "author": "NetAdmin",
                    "date": "2023-08-15",
                    "content": "Common qBittorrent connection problems and solutions. Check your port forwarding, VPN settings, and firewall configuration. Make sure your client is allowed through Windows Firewall and any antivirus software.",
                    "settings_code": "[Connection]\nport=6881\nupnp=true\nproxy_type=1\nproxy_host=your-vpn-ip\nproxy_port=1080"
                }
            },
            {
                "success": True,
                "url": "https://www.myanonamouse.net/f/789/qbittorrent-performance-tuning",
                "title": "qBittorrent Performance Tuning",
                "crawled_at": datetime.now().isoformat(),
                "data": {
                    "title": "qBittorrent Performance Tuning",
                    "author": "SpeedDemon",
                    "date": "2024-01-10",
                    "content": "Advanced qBittorrent performance tuning for MAM users. Optimize disk I/O, memory usage, and network settings for maximum throughput. Regular maintenance and proper configuration can significantly improve download speeds.",
                    "settings_code": "[Advanced]\ndisk_write_cache_size=64\ndisk_write_cache_ttl=60\nos_cache=true\nsave_resume_data_interval=60\nrecheck_completed_torrents=true"
                }
            }
        ]

        # Process and output in Markdown
        guides_md = processor.process_guides_data(sample_guides_data)
        qb_md = processor.process_qbittorrent_data(sample_qb_data)

        processor.save_markdown_output(guides_md, qb_md)
        logger.info("Demo mode completed - check mam_crawl_output.md for results")

    else:
        # Real crawling mode
        logger.info("Starting real crawl...")
        crawler = MAMPassiveCrawler()
        processor = MAMDataProcessor()
        
        # Crawl guides
        logger.info("Crawling guides section...")
        guides_data = await crawler.crawl_guides_section()
        
        # Crawl qBittorrent settings
        logger.info("Crawling qBittorrent settings...")
        qb_data = await crawler.crawl_qbittorrent_settings()
        
        # Process and save
        guides_md = processor.process_guides_data(guides_data)
        qb_md = processor.process_qbittorrent_data(qb_data)
        processor.save_markdown_output(guides_md, qb_md)
        
        # Trigger RAG ingestion
        crawler.trigger_ingestion()


if __name__ == "__main__":
    asyncio.run(main())