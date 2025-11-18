"""
Centralized configuration for MAMcrawler.
Single source of truth for all constants and settings.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

# Shared user agents (kept up-to-date)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Allowed paths (single source of truth)
ALLOWED_PATHS = [
    "/",              # homepage
    "/t/",            # torrent pages (public)
    "/tor/browse.php",  # browse page
    "/tor/search.php",  # search results
    "/guides/",       # guides section
    "/f/",            # forum sections (public)
]

# Forbidden patterns
FORBIDDEN_PATTERNS = [
    "/user/", "/account/", "/admin/", "/mod/",
    "/login", "/register", "/upload", "/download", "/api/"
]


@dataclass
class CrawlerConfig:
    """Configuration for basic crawler."""
    base_url: str = "https://www.myanonamouse.net"
    min_delay: int = 3
    max_delay: int = 10
    session_timeout: int = 7200  # 2 hours in seconds
    max_content_length: int = 5000
    max_pages_per_session: int = 50


@dataclass
class StealthConfig(CrawlerConfig):
    """Configuration for stealth crawler with human-like behavior."""
    min_delay: int = 10
    max_delay: int = 30
    scroll_delay: int = 2
    read_delay: int = 5
    viewports: List[Tuple[int, int]] = field(default_factory=lambda: [
        (1920, 1080),
        (1366, 768),
        (1536, 864),
        (1440, 900),
        (1600, 900)
    ])


@dataclass
class RAGConfig:
    """Configuration for RAG system."""
    model_name: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    index_path: str = "index.faiss"
    db_path: str = "metadata.sqlite"
    top_k: int = 5
    llm_model: str = "claude-haiku-4-5"
    max_tokens: int = 1500
    headers_to_split: List[Tuple[str, str]] = field(default_factory=lambda: [
        ("#", "H1"),
        ("##", "H2"),
        ("###", "H3")
    ])


@dataclass
class OutputConfig:
    """Configuration for output directories and files."""
    guides_dir: str = "guides_output"
    forum_dir: str = "forum_qbittorrent_output"
    state_file: str = "crawler_state.json"
    log_file: str = "stealth_crawler.log"


# Default instances for easy import
DEFAULT_CRAWLER_CONFIG = CrawlerConfig()
DEFAULT_STEALTH_CONFIG = StealthConfig()
DEFAULT_RAG_CONFIG = RAGConfig()
DEFAULT_OUTPUT_CONFIG = OutputConfig()
