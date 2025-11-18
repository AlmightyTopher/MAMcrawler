"""
Configuration and procedures for MyAnonamouse.net passive crawling.
This file contains the specific crawling guidelines and procedures for MAM.
"""

from typing import Dict, List, Any
import json

class MAMCrawlingProcedures:
    """
    Contains the specific procedures and guidelines for crawling MyAnonamouse.net.
    This is designed to be dynamically updated based on new information.
    """

    def __init__(self):
        self.allowed_endpoints = {
            "homepage": "/",
            "browse": "/tor/browse.php",
            "search": "/tor/search.php",
            "torrent_details": "/t/",  # Public torrent pages only
            "category_browse": "/tor/browse.php?cat=",
        }

        self.forbidden_patterns = [
            "/user/",  # User profiles
            "/account/",  # Account pages
            "/admin/",  # Admin areas
            "/mod/",  # Moderator areas
            "/login",  # Login pages
            "/register",  # Registration
            "/upload",  # Upload pages
            "/download",  # Direct download links
            "/api/",  # API endpoints
        ]

        self.rate_limits = {
            "min_delay": 3,  # seconds between requests
            "max_delay": 10,  # maximum delay
            "max_pages_per_session": 50,  # pages per crawling session
            "session_timeout": 3600,  # 1 hour session timeout
        }

        self.extraction_schemas = {
            "torrent_list": {
                "name": "TorrentList",
                "fields": [
                    {"name": "title", "selector": "a[href*='/t/']", "type": "text"},
                    {"name": "category", "selector": ".category", "type": "text"},
                    {"name": "size", "selector": ".size", "type": "text"},
                    {"name": "seeders", "selector": ".seeders", "type": "text"},
                    {"name": "leechers", "selector": ".leechers", "type": "text"},
                ]
            },
            "torrent_details": {
                "name": "TorrentDetails",
                "fields": [
                    {"name": "title", "selector": "h1", "type": "text"},
                    {"name": "description", "selector": ".description", "type": "text"},
                    {"name": "category", "selector": ".category", "type": "text"},
                    {"name": "size", "selector": ".size", "type": "text"},
                    {"name": "uploaded_by", "selector": ".uploaded_by", "type": "text"},
                    {"name": "upload_date", "selector": ".upload_date", "type": "text"},
                ]
            }
        }

    def is_allowed_url(self, url: str) -> bool:
        """Check if a URL is allowed for passive crawling."""
        from urllib.parse import urlparse
        parsed = urlparse(url)

        # Must be on myanonamouse.net
        if "myanonamouse.net" not in parsed.netloc:
            return False

        # Check forbidden patterns
        path = parsed.path.lower()
        for forbidden in self.forbidden_patterns:
            if forbidden in path:
                return False

        # Check allowed endpoints
        for allowed in self.allowed_endpoints.values():
            if path.startswith(allowed):
                return True

        return False

    def get_extraction_config(self, page_type: str) -> Dict[str, Any]:
        """Get extraction configuration for a specific page type."""
        if page_type in self.extraction_schemas:
            return {
                "type": "css_selector",
                "params": self.extraction_schemas[page_type]
            }
        return {}

    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration."""
        return self.rate_limits.copy()

    def update_procedures(self, new_procedures: Dict[str, Any]):
        """Dynamically update crawling procedures."""
        # This method allows for dynamic updates to procedures
        # based on new information or site changes

        if "allowed_endpoints" in new_procedures:
            self.allowed_endpoints.update(new_procedures["allowed_endpoints"])

        if "forbidden_patterns" in new_procedures:
            self.forbidden_patterns.extend(new_procedures["forbidden_patterns"])

        if "rate_limits" in new_procedures:
            self.rate_limits.update(new_procedures["rate_limits"])

        if "extraction_schemas" in new_procedures:
            self.extraction_schemas.update(new_procedures["extraction_schemas"])

    def save_procedures(self, filepath: str):
        """Save current procedures to file."""
        procedures = {
            "allowed_endpoints": self.allowed_endpoints,
            "forbidden_patterns": self.forbidden_patterns,
            "rate_limits": self.rate_limits,
            "extraction_schemas": self.extraction_schemas,
        }

        with open(filepath, 'w') as f:
            json.dump(procedures, f, indent=2)

    def load_procedures(self, filepath: str):
        """Load procedures from file."""
        try:
            with open(filepath, 'r') as f:
                procedures = json.load(f)

            self.allowed_endpoints = procedures.get("allowed_endpoints", self.allowed_endpoints)
            self.forbidden_patterns = procedures.get("forbidden_patterns", self.forbidden_patterns)
            self.rate_limits = procedures.get("rate_limits", self.rate_limits)
            self.extraction_schemas = procedures.get("extraction_schemas", self.extraction_schemas)

        except FileNotFoundError:
            pass  # Use defaults if file doesn't exist


# Global instance
mam_procedures = MAMCrawlingProcedures()