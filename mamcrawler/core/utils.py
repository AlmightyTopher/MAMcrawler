"""
Shared Utilities Module for MAMcrawler Project

This module provides common utilities that can be used across all crawler components,
eliminating code duplication and ensuring consistency.

Author: Audiobook Automation System
Version: 1.0.0
"""

import asyncio
import hashlib
import logging
import os
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from urllib.parse import urlparse, urljoin


class MAMUtils:
    """
    Utility class containing common functions used across MAMcrawler.
    Provides static methods for common operations.
    """
    
    # Updated and consolidated user agents list
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    # Viewport options for stealth behavior
    VIEWPORTS = [
        (1920, 1080),
        (1366, 768),
        (1536, 864),
        (1440, 900),
        (1600, 900),
        (1536, 864)
    ]
    
    # Allowed paths for crawling
    ALLOWED_PATHS = [
        "/",           # homepage
        "/t/",         # torrent pages (public)
        "/tor/browse.php",  # browse page
        "/tor/search.php",  # search results
        "/guides/",    # guides section
        "/f/",         # forum sections (public)
    ]
    
    # Rate limiting constants
    DEFAULT_MIN_DELAY = 3
    DEFAULT_MAX_DELAY = 10
    
    @staticmethod
    def get_random_user_agent() -> str:
        """
        Get a random user agent from the list.
        
        Returns:
            Random user agent string
        """
        return random.choice(MAMUtils.USER_AGENTS)
    
    @staticmethod
    def get_random_viewport() -> Tuple[int, int]:
        """
        Get a random viewport size for stealth behavior.
        
        Returns:
            Tuple of (width, height)
        """
        return random.choice(MAMUtils.VIEWPORTS)
    
    @staticmethod
    def sanitize_filename(title: str, max_length: int = 100) -> str:
        """
        Convert title to safe filename.
        
        Args:
            title: The title to sanitize
            max_length: Maximum length of the filename
            
        Returns:
            Sanitized filename
        """
        if not title:
            return "untitled"
        
        # Remove special characters except spaces, hyphens, underscores
        filename = re.sub(r'[<>:"/\\|?*]', '', title)
        
        # Replace whitespace and punctuation with underscores
        filename = re.sub(r'[\s\-]+', '_', filename)
        
        # Remove consecutive underscores
        filename = re.sub(r'_+', '_', filename)
        
        # Remove leading/trailing underscores
        filename = filename.strip('_')
        
        # Limit length
        if len(filename) > max_length:
            filename = filename[:max_length]
        
        return filename or "untitled"
    
    @staticmethod
    def is_allowed_path(url: str) -> bool:
        """
        Check if the URL path is allowed for crawling.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the URL path is allowed
        """
        if not url:
            return False
            
        parsed = urlparse(url)
        
        # Must be on the correct domain
        if parsed.netloc != "www.myanonamouse.net":
            return False

        # Check against allowed paths
        path = parsed.path
        for allowed in MAMUtils.ALLOWED_PATHS:
            # Handle homepage as exact match only
            if allowed == "/" and path == "/":
                return True
            # For other paths, check prefix but not for "/"
            elif allowed != "/" and path.startswith(allowed):
                return True

        return False
    
    @staticmethod
    def extract_category_from_url(url: str) -> str:
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
    
    @staticmethod
    def anonymize_content(content: str, max_length: int = 5000) -> str:
        """
        Anonymize content by removing sensitive information.
        
        Args:
            content: The content to anonymize
            max_length: Maximum length to return
            
        Returns:
            Anonymized content
        """
        if not content:
            return ""
        
        # Remove email addresses
        content = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL]', content
        )
        
        # Remove potential usernames (variations)
        content = re.sub(r'\buser[_-]?\w+\b', '[USER]', content, flags=re.IGNORECASE)
        content = re.sub(r'\b[Uu]\w{1,10}\s+[Ss]ays\b', '[USER_SAYS]', content)
        
        # Remove potential session or token information
        content = re.sub(r'sid=[a-f0-9]{32}', 'sid=[TOKEN]', content, flags=re.IGNORECASE)
        content = re.sub(r'session=[a-f0-9]{32}', 'session=[TOKEN]', content, flags=re.IGNORECASE)
        
        # Limit length
        return content[:max_length]
    
    @staticmethod
    def generate_id(content: str) -> str:
        """
        Generate a unique ID from content.
        
        Args:
            content: The content to hash
            
        Returns:
            MD5 hash of the content
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        Check if URL is valid.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if URL is valid
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def make_absolute_url(base_url: str, relative_url: str) -> str:
        """
        Convert relative URL to absolute URL.
        
        Args:
            base_url: The base URL
            relative_url: The relative URL
            
        Returns:
            Absolute URL
        """
        return urljoin(base_url, relative_url)
    
    @staticmethod
    def extract_domain(url: str) -> str:
        """
        Extract domain from URL.
        
        Args:
            url: The URL to extract domain from
            
        Returns:
            Domain string
        """
        try:
            return urlparse(url).netloc
        except Exception:
            return ""
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f}{size_names[i]}"
    
    @staticmethod
    def parse_duration(duration_str: str) -> Optional[int]:
        """
        Parse duration string and return total seconds.
        
        Args:
            duration_str: Duration string (e.g., "1:30:45", "45:30", "30")
            
        Returns:
            Total seconds or None if parsing failed
        """
        if not duration_str:
            return None
        
        try:
            parts = duration_str.split(':')
            if len(parts) == 1:
                # Just seconds
                return int(parts[0])
            elif len(parts) == 2:
                # Minutes:seconds
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                # Hours:minutes:seconds
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return None
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """
        Format duration in human readable format.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 0:
            return "0s"
        
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02}:{seconds:02}"
        else:
            return f"{minutes}:{seconds:02}"
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean text by removing extra whitespace and normalizing.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove multiple whitespaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """
        Extract all numbers from text.
        
        Args:
            text: Text to extract numbers from
            
        Returns:
            List of numbers found in text
        """
        if not text:
            return []
        
        # Find all numbers (including decimals)
        numbers = re.findall(r'\d+\.?\d*', text)
        
        try:
            return [float(num) for num in numbers]
        except ValueError:
            return []
    
    @staticmethod
    def generate_stealth_js() -> str:
        """
        Generate JavaScript for human-like behavior simulation.
        
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
    
    @staticmethod
    def create_logger(name: str, level: str = logging.INFO) -> logging.Logger:
        """
        Create a standardized logger.
        
        Args:
            name: Logger name
            level: Logging level
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        return logger


class RateLimiter:
    """
    Rate limiter class for managing request rates.
    """
    
    def __init__(self, min_delay: float = None, max_delay: float = None):
        """
        Initialize rate limiter.
        
        Args:
            min_delay: Minimum delay between requests
            max_delay: Maximum delay between requests
        """
        self.min_delay = min_delay or MAMUtils.DEFAULT_MIN_DELAY
        self.max_delay = max_delay or MAMUtils.DEFAULT_MAX_DELAY
        self.last_request = None
    
    async def wait(self):
        """Wait the appropriate amount of time between requests."""
        if self.last_request is not None:
            elapsed = time.time() - self.last_request
            if elapsed < self.min_delay:
                delay = random.uniform(self.min_delay, self.max_delay)
                await asyncio.sleep(delay)
        
        self.last_request = time.time()


class RetryPolicy:
    """
    Retry policy for handling failed operations.
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 5.0):
        """
        Initialize retry policy.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute_with_retry(self, operation):
        """
        Execute operation with retry logic and exponential backoff.
        
        Args:
            operation: Async operation to execute
            
        Returns:
            Result of the operation
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    # Exponential backoff
                    delay = (2 ** (attempt - 1)) * self.base_delay
                    await asyncio.sleep(delay)
        
        # All retries failed
        raise last_exception


class ConfigManager:
    """
    Centralized configuration management.
    """
    
    @staticmethod
    def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        config_path = Path(config_path)
        if not config_path.exists():
            return {}
        
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config from {config_path}: {e}")
            return {}
    
    @staticmethod
    def save_config(config: Dict[str, Any], config_path: Union[str, Path]):
        """
        Save configuration to file.
        
        Args:
            config: Configuration dictionary
            config_path: Path to save configuration
        """
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            import json
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Failed to save config to {config_path}: {e}")
    
    @staticmethod
    def get_env_var(key: str, default: Any = None, required: bool = False) -> Any:
        """
        Get environment variable with validation.
        
        Args:
            key: Environment variable key
            default: Default value if not found
            required: Whether the variable is required
            
        Returns:
            Environment variable value
        """
        value = os.getenv(key, default)
        
        if required and (value is None or value == ''):
            raise ValueError(f"Required environment variable '{key}' is not set")
        
        return value


# Export main classes for easy importing
__all__ = [
    'MAMUtils',
    'RateLimiter',
    'RetryPolicy',
    'ConfigManager'
]