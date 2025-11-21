"""
Abstract Base Crawler for MAMcrawler Project

This module provides a unified base class for all crawler implementations,
consolidating common functionality and eliminating code duplication.

Author: Audiobook Automation System
Version: 1.0.0
"""

import asyncio
import os
import re
import random
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BaseMAMCrawler(ABC):
    """
    Abstract base class for all MAM crawlers.
    Provides common functionality for authentication, rate limiting, 
    user agent management, and data processing.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the base crawler with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        # Default configuration
        self.config = config or {}
        
        # Authentication
        self.username = self.config.get('username') or os.getenv('MAM_USERNAME')
        self.password = self.config.get('password') or os.getenv('MAM_PASSWORD')
        self.base_url = "https://www.myanonamouse.net"
        
        # Session management
        self.session_cookies = None
        self.last_login = None
        self.login_expiry = timedelta(hours=2)
        
        # Rate limiting
        self.min_delay = self.config.get('min_delay', 3)
        self.max_delay = self.config.get('max_delay', 10)
        self.last_request = datetime.now()
        
        # User agent rotation - Updated and consolidated list
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        # Allowed paths for crawling
        self.allowed_paths = [
            "/",           # homepage
            "/t/",         # torrent pages (public)
            "/tor/browse.php",  # browse page
            "/tor/search.php",  # search results
            "/guides/",    # guides section
            "/f/",         # forum sections (public)
        ]
        
        # Viewport options for stealth behavior
        self.viewports = [
            (1920, 1080),
            (1366, 768),
            (1536, 864),
            (1440, 900),
            (1600, 900),
            (1536, 864)
        ]
        
        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup consistent logging configuration."""
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid authenticated session."""
        now = datetime.now()
        return (
            self.last_login is not None and
            now - self.last_login <= self.login_expiry and
            self.session_cookies is not None
        )

    async def rate_limit(self):
        """
        Implement rate limiting to avoid detection.
        Can be overridden by subclasses for custom behavior.
        """
        now = datetime.now()
        elapsed = (now - self.last_request).total_seconds()

        if elapsed < self.min_delay:
            delay = random.uniform(self.min_delay, self.max_delay)
            self.logger.info(f"Rate limiting: sleeping for {delay:.2f} seconds")
            await asyncio.sleep(delay)

        self.last_request = datetime.now()

    def get_random_user_agent(self) -> str:
        """Get a random user agent from the list."""
        return random.choice(self.user_agents)

    def get_random_viewport(self) -> Tuple[int, int]:
        """Get a random viewport size for stealth behavior."""
        return random.choice(self.viewports)

    def sanitize_filename(self, title: str, max_length: int = 100) -> str:
        """
        Convert title to safe filename.
        
        Args:
            title: The title to sanitize
            max_length: Maximum length of the filename
            
        Returns:
            Sanitized filename
        """
        # Remove special characters
        filename = re.sub(r'[<>:"/\\|?*]', '', title)
        # Replace whitespace with underscores
        filename = re.sub(r'\s+', '_', filename)
        # Limit length
        return filename[:max_length]

    def is_allowed_path(self, url: str) -> bool:
        """
        Check if the URL path is allowed for crawling.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the URL path is allowed
        """
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

    def extract_category_from_url(self, url: str) -> str:
        """
        Extract category from URL.
        
        Args:
            url: The URL to extract category from
            
        Returns:
            Category string
        """
        if '?gid=' in url:
            return "Guide"
        
        path_parts = url.rstrip('/').split('/')
        if len(path_parts) >= 2:
            category = path_parts[-2] if path_parts[-1] else path_parts[-2]
            if category != 'guides':
                return category.replace('-', ' ').replace('_', ' ').title()
        return "General"

    def anonymize_content(self, content: str, max_length: int = 5000) -> str:
        """
        Anonymize content by removing sensitive information.
        
        Args:
            content: The content to anonymize
            max_length: Maximum length to return
            
        Returns:
            Anonymized content
        """
        if not content:
            return content
        
        # Remove email addresses
        content = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL]', content
        )
        
        # Remove potential usernames
        content = re.sub(r'\buser[_-]\w+\b', '[USER]', content, flags=re.IGNORECASE)
        
        # Limit length
        return content[:max_length]

    async def authenticate(self) -> bool:
        """
        Authenticate with MAM.
        Must be implemented by subclasses.
        
        Returns:
            True if authentication successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement authenticate method")

    async def ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid authenticated session.
        
        Returns:
            True if authenticated, False otherwise
        """
        if self.is_authenticated:
            return True
            
        self.logger.info("Authenticating with MyAnonamouse.net")
        success = await self.authenticate()
        if not success:
            self.logger.error("Authentication failed")
            return False
            
        return True

    @abstractmethod
    async def crawl_page(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Crawl a single page.
        Must be implemented by subclasses.
        
        Args:
            url: The URL to crawl
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing crawl results
        """
        pass

    async def crawl_with_retry(self, url: str, max_retries: int = 3, **kwargs) -> Dict[str, Any]:
        """
        Crawl a page with retry logic and exponential backoff.
        
        Args:
            url: The URL to crawl
            max_retries: Maximum number of retry attempts
            **kwargs: Additional parameters for crawl_page
            
        Returns:
            Dictionary containing crawl results
        """
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"Crawling {url} (attempt {attempt}/{max_retries})")
                
                # Ensure authentication
                if not await self.ensure_authenticated():
                    return {
                        'success': False,
                        'error': 'Authentication failed',
                        'url': url,
                        'attempt': attempt
                    }
                
                # Rate limit before crawling
                await self.rate_limit()
                
                # Attempt to crawl
                result = await self.crawl_page(url, **kwargs)
                result['attempt'] = attempt
                return result
                
            except Exception as e:
                self.logger.error(f"Error on attempt {attempt}: {e}")
                
                if attempt < max_retries:
                    # Exponential backoff
                    backoff = (2 ** attempt) * 5  # 10s, 20s, 40s
                    self.logger.info(f"Backing off for {backoff} seconds before retry...")
                    await asyncio.sleep(backoff)
        
        # All retries failed
        return {
            'success': False,
            'error': 'Max retries exceeded',
            'url': url,
            'attempts': max_retries
        }

    def create_stealth_js(self) -> str:
        """
        Create JavaScript for human-like behavior simulation.
        Can be overridden by subclasses for custom behavior.
        
        Returns:
            JavaScript code string
        """
        return """
        // Simulate human-like mouse movement
        async function simulateHumanBehavior() {
            // Random mouse movements
            for (let i = 0; i < 3; i++) {
                const x = Math.floor(Math.random() * window.innerWidth);
                const y = Math.floor(Math.random() * window.innerHeight);

                const event = new MouseEvent('mousemove', {
                    clientX: x,
                    clientY: y,
                    bubbles: true
                });
                document.dispatchEvent(event);

                await new Promise(resolve => setTimeout(resolve, 200 + Math.random() * 300));
            }

            // Scroll like a human reading
            const scrollHeight = document.documentElement.scrollHeight;
            const viewportHeight = window.innerHeight;
            const scrollSteps = 3 + Math.floor(Math.random() * 3);

            for (let i = 0; i < scrollSteps; i++) {
                const scrollTo = (scrollHeight / scrollSteps) * (i + 1);
                window.scrollTo({
                    top: scrollTo,
                    behavior: 'smooth'
                });

                // Pause to "read"
                await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));
            }

            // Scroll back to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
            await new Promise(resolve => setTimeout(resolve, 500));
        }

        await simulateHumanBehavior();
        """

    def save_guide_to_file(self, guide_data: Dict[str, Any], output_dir: Path) -> Optional[Path]:
        """
        Save guide data to markdown file.
        
        Args:
            guide_data: Guide data dictionary
            output_dir: Output directory path
            
        Returns:
            Path to saved file or None if failed
        """
        if not guide_data.get('success'):
            return None
            
        filename = self.sanitize_filename(guide_data['title']) + ".md"
        filepath = output_dir / filename

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

        # Add related links
        sub_links = guide_data.get('sub_links') or guide_data.get('links', {}).get('internal', [])
        if sub_links:
            content += "## Related Guides\n\n"
            for link in sub_links[:20]:
                if isinstance(link, dict):
                    content += f"- [{link['title']}]({link['url']})\n"
                else:
                    content += f"- {link}\n"
            content += "\n---\n\n"

        content += "## Content\n\n"
        content += guide_data.get('content', 'No content extracted')

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.info(f"Saved guide to {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to save guide: {e}")
            return None

    def validate_crawl_result(self, result: Dict[str, Any]) -> bool:
        """
        Validate crawl result for completeness.
        
        Args:
            result: The crawl result to validate
            
        Returns:
            True if result is valid and complete
        """
        required_fields = ["success", "url", "crawled_at"]
        return all(field in result for field in required_fields) and result["success"]