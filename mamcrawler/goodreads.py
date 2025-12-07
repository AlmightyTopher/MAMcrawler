"""
Goodreads Metadata Stub
Placeholder for missing Goodreads integration.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class GoodreadsMetadata:
    """
    Stub for Goodreads metadata retrieval.
    """
    
    def __init__(self):
        pass
        
    async def search_book(self, title: str, author: str) -> Optional[Dict]:
        """
        Search for book metadata.
        
        Args:
            title: Book title
            author: Author name
            
        Returns:
            Metadata dict or None
        """
        logger.warning("Goodreads integration is currently a stub. No data returned.")
        return None
