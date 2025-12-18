import os
import json
import logging
import asyncio
import aiohttp
from typing import List, Dict, Set
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class DiscoveryService:
    """
    Service for discovering new audiobooks and scanning existing library.
    Ported from execute_real_workflow_final_real.py
    """

    async def scan_library(self) -> Dict:
        """Get complete library inventory from AudiobookShelf"""
        try:
            abs_url = settings.ABS_URL
            abs_token = settings.ABS_TOKEN
            
            if not abs_token:
                logger.error("ABS_TOKEN not set")
                return {}

            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {abs_token}'}

                # Get first library
                async with session.get(
                    f'{abs_url}/api/libraries',
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to get libraries: {resp.status}")
                        return {}
                        
                    data = await resp.json()
                    libs = data.get('libraries', [])
                    if not libs:
                        logger.error("No libraries found in ABS")
                        return {}
                        
                    lib_id = libs[0]['id']
                    lib_name = libs[0]['name']

                logger.info(f"Scanning library: {lib_name}")

                all_items = []
                offset = 0
                
                # Fetch all items
                while True:
                    async with session.get(
                        f'{abs_url}/api/libraries/{lib_id}/items',
                        headers=headers,
                        params={'limit': 500, 'offset': offset}
                    ) as resp:
                        if resp.status != 200:
                            break
                            
                        result = await resp.json()
                        items = result.get('results', [])

                        if not items:
                            break

                        all_items.extend(items)
                        offset += 500
                        logger.info(f"Loaded {len(all_items)} items...")

                # Extract existing books
                existing = {
                    'titles': set(),
                    'authors': set(),
                    'series': set(),
                }

                for item in all_items:
                    metadata = item.get('media', {}).get('metadata', {})
                    title = metadata.get('title', '').strip()
                    author = metadata.get('author', '').strip()
                    series = metadata.get('seriesName', '').strip()

                    if title:
                        existing['titles'].add(title.lower())
                    if author:
                        existing['authors'].add(author.lower())
                    if series:
                        existing['series'].add(series.lower())

                return {
                    'library_id': lib_id,
                    'total_items': len(all_items),
                    'existing': existing
                }

        except Exception as e:
            logger.error(f"Failed to scan library: {e}")
            return {}

    def load_download_list(self) -> List[Dict]:
        """Load audiobooks to download from Postgres DB"""
        try:
            from backend.database import get_db_context
            from backend.models.download import Download
            
            with get_db_context() as db:
                downloads = db.query(Download).filter(Download.status == "queued").all()
                logger.info(f"Loaded {len(downloads)} books from Download table")
                return [
                    {
                        "title": d.title, 
                        "author": d.author, 
                        "db_id": d.id,
                        # Pass DB limits/tracking if needed
                    } 
                    for d in downloads
                ]
        except Exception as e:
            logger.error(f"Failed to load download list from DB: {e}")
            return []

    async def find_new_books(self) -> List[Dict]:
        """Find books in download list that are not in library"""
        scan_result = await self.scan_library()
        if not scan_result:
            return []

        existing_titles = scan_result['existing']['titles']
        download_list = self.load_download_list()
        
        new_books = []
        for book in download_list:
            title = book.get('title', '').strip().lower()
            if title and title not in existing_titles:
                new_books.append(book)
                
        logger.info(f"Found {len(new_books)} new books to acquire")
        return new_books

    def queue_downloads(self, books: List[Dict]) -> int:
        """
        Queue new books for download in the database.
        
        Args:
            books: List of book dictionaries with 'title', 'author'
            
        Returns:
            Count of newly queued items
        """
        try:
            from backend.database import get_db_context
            from backend.models.download import Download
            
            count = 0
            with get_db_context() as db:
                for book in books:
                    title = book.get('title', '').strip()
                    author = book.get('author', '').strip()
                    
                    if not title:
                        continue
                        
                    # Check duplication
                    exists = db.query(Download).filter(
                        Download.title == title,
                        Download.author == author
                    ).first()
                    
                    if not exists:
                        new_dl = Download(
                            title=title,
                            author=author,
                            source="discovery_service",
                            status="queued",
                            priority=book.get('priority', 10)
                        )
                        db.add(new_dl)
                        count += 1
                        logger.info(f"Queued for download: {title} by {author}")
                
                db.commit()
                return count

        except Exception as e:
            logger.error(f"Failed to queue downloads: {e}")
            return 0
