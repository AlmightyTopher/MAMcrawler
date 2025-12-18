
import asyncio
import logging
import html
import re
from difflib import SequenceMatcher
import feedparser
from typing import List, Optional, Dict
from datetime import datetime

from backend.config import get_settings
from backend.integrations.abs_client import AudiobookshelfClient
from backend.integrations.hardcover_client import HardcoverClient

logger = logging.getLogger(__name__)
settings = get_settings()

class GoodreadsService:
    """
    Service to sync Goodreads 'Read' shelf with Audiobookshelf and Hardcover.
    Ported from goodreads_sync.py
    """
    
    def __init__(self):
        self.rss_url = settings.GOODREADS_RSS_URL
        self.abs_cache = []

    async def sync_goodreads(self) -> Dict[str, int]:
        """
        Main entry point: Sync Goodreads RSS to ABS and Hardcover
        Returns statistics of the run
        """
        logger.info("Starting Goodreads Sync...")
        stats = {"processed": 0, "abs_updated": 0, "hardcover_updated": 0, "errors": 0}

        try:
            # Initialize clients
            async with AudiobookshelfClient(settings.ABS_URL, settings.ABS_TOKEN) as abs_client:
                # 0. Get User ID (Assuming single user or specific user 'TopherGutbrod')
                user_id = await self._get_abs_user_id(abs_client, "TopherGutbrod")
                if not user_id:
                    # Fallback to first admin user if TopherGutbrod not found
                    logger.warning("User 'TopherGutbrod' not found. Falling back to first admin user.")
                    user_id = await self._get_first_admin_id(abs_client)
                    
                if not user_id:
                    logger.error("No valid ABS user found for sync.")
                    return stats

                # 1. Build Brute Force Cache
                await self._build_abs_library_cache(abs_client)

                async with HardcoverClient(settings.HARDCOVER_TOKEN) as hc_client:
                    # Pagination loop
                    page = 1
                    while True:
                        logger.info(f"Fetching RSS Page {page}...")
                        feed_url = f"{self.rss_url}&page={page}"
                        feed = await asyncio.to_thread(feedparser.parse, feed_url)
                        
                        if not feed or not feed.entries:
                            logger.info("No more entries found. Sync complete.")
                            break
                        
                        logger.info(f"Page {page}: Found {len(feed.entries)} books.")
                        
                        for entry in feed.entries:
                            stats["processed"] += 1
                            try:
                                processed = await self._process_book(entry, abs_client, hc_client)
                                if processed.get("abs_updated"): stats["abs_updated"] += 1
                                if processed.get("hardcover_updated"): stats["hardcover_updated"] += 1
                            except Exception as e:
                                logger.error(f"Error processing book '{entry.get('title', 'Unknown')}': {e}")
                                stats["errors"] += 1
                            
                            # Rate limits
                            await asyncio.sleep(1) # Reduced from 10s for responsiveness, check APIs
                        
                        if len(feed.entries) < 100:
                            break
                        page += 1

        except Exception as e:
            logger.error(f"Goodreads Sync Failed: {e}", exc_info=True)
            raise

        logger.info(f"Goodreads Sync Complete. Stats: {stats}")
        return stats

    async def _get_abs_user_id(self, client: AudiobookshelfClient, username: str) -> Optional[str]:
        try:
            users_resp = await client.users.get_users()
            for u in users_resp.get("users", []):
                if u["username"].lower() == username.lower():
                    return u["id"]
        except Exception as e:
            logger.error(f"Error fetching ABS users: {e}")
        return None

    async def _get_first_admin_id(self, client: AudiobookshelfClient) -> Optional[str]:
        try:
            users_resp = await client.users.get_users()
            for u in users_resp.get("users", []):
                if u.get("type") == "admin": 
                     return u["id"]
            # Fallback to any user
            if users_resp.get("users"):
                return users_resp["users"][0]["id"]
        except Exception as e:
             logger.error(f"Error fetching ABS users fallback: {e}")
        return None

    async def _build_abs_library_cache(self, client: AudiobookshelfClient):
        """Build local cache of all ABS items for brute force matching"""
        logger.info("Building ABS library cache...")
        self.abs_cache = []
        try:
            libs = await client.get_libraries()
            if not libs:
                return
            
            lib_id = libs[0]['id']
            # Fetch all items (paginated internally by client if needed, but here we ask for huge limit)
            # Actually abs_client.get_library_items handles pagination if we loop, but here we want all.
            # Client has get_library_items with auto-pagination logic? Let's check client code.
            # Yes, get_library_items paginates until completion if limit is high enough or loop is used? 
            # The client implementation viewed earlier loops until total is reached if we call it right?
            # Actually the client implementation shown earlier loops if we call it with a loop, 
            # OR logic inside "get_library_items" has a while True loop?
            # Looking at lines 206-235 of abs_client.py: Yes, it loops until all items are fetched. PERFECT.
            all_items = await client.get_library_items(library_id=lib_id, limit=1000) 
            
            logger.info(f"Cached {len(all_items)} books from ABS.")
            
            for item in all_items:
                media = item.get('media', {})
                metadata = media.get('metadata', {})
                title = metadata.get('title', '')
                author = metadata.get('authorName', '')
                
                if title:
                    self.abs_cache.append({
                        'id': item['id'],
                        'title': title,
                        'clean_title': self._clean_string(title),
                        'author': author,
                        'clean_author': self._clean_string(author),
                        'duration': media.get('duration', 0),
                        'raw_item': item
                    })
        except Exception as e:
            logger.error(f"Failed to build cache: {e}")

    def _clean_string(self, text: str) -> str:
        if not text: return ""
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'[^\w\s]', '', text)
        return " ".join(text.split()).lower()

    async def _brute_force_match(self, title: str, author: str) -> Optional[Dict]:
        clean_title = self._clean_string(title)
        clean_author = self._clean_string(author)
        
        matches = []
        for item in self.abs_cache:
            score = 0
            if clean_title == item['clean_title']:
                score += 100
            else:
                ratio = SequenceMatcher(None, clean_title, item['clean_title']).ratio()
                if ratio > 0.85:
                    score += int(ratio * 90)
                elif clean_title in item['clean_title'] and len(clean_title) > 5:
                    score += 40
            
            if score > 0:
                if clean_author and item['clean_author']:
                    if clean_author in item['clean_author']:
                        score += 30
                    elif SequenceMatcher(None, clean_author, item['clean_author']).ratio() > 0.8:
                        score += 20
                        
            matches.append((score, item))
        
        matches.sort(key=lambda x: x[0], reverse=True)
        
        if matches and matches[0][0] >= 80:
             return matches[0][1]['raw_item']
        return None

    async def _process_book(self, entry, abs_client: AudiobookshelfClient, hc_client: HardcoverClient):
        result = {"abs_updated": False, "hardcover_updated": False}
        
        title = html.unescape(entry.get('title', ''))
        author = html.unescape(entry.get('author_name', ''))
        isbn = entry.get('isbn')
        user_shelves = entry.get('user_shelves', '')
        
        author = " ".join(author.split()) # Clean author name
        
        # Determine strict read status (Goodreads has shelves like 'read', 'currently-reading', 'to-read')
        is_read = False
        if entry.get('user_read_at'):
            is_read = True
        else:
            # Check shelves
            shelf_names = []
            if isinstance(user_shelves, list):
                for s in user_shelves:
                    if isinstance(s, dict): shelf_names.append(s.get('term') or s.get('label'))
                    else: shelf_names.append(str(s))
            else:
                shelf_names.append(str(user_shelves))
            
            if 'read' in shelf_names: is_read = True
            # Exclude non-finished
            if 'to-read' in shelf_names or 'currently-reading' in shelf_names:
                is_read = False
                
        if not is_read:
            return result

        # ABS Sync
        found_item = await self._brute_force_match(title, author)
        if found_item:
            # Check current progress to avoid redundant updates?
            # For now, just enforce "Finished"
            try:
                media = found_item.get('media', {})
                duration = media.get('duration', 0)
                
                # Check if already finished? 
                user_media = found_item.get('userMedia', {})
                if not user_media.get('isFinished'):
                     await abs_client.progress.update_media_progress(
                        library_item_id=found_item['id'],
                        progress=1.0,
                        current_time=duration,
                        is_finished=True
                     )
                     logger.info(f"Marked '{title}' as READ in ABS")
                     result["abs_updated"] = True
            except Exception as e:
                logger.error(f"Failed ABS update for {title}: {e}")
        
        # Hardcover Sync
        if settings.HARDCOVER_TOKEN:
            try:
                clean_title_hc = title.split('(')[0].strip()
                match = await hc_client.resolve_book(clean_title_hc, author, isbn)
                
                if match.success and match.book:
                    # Update status
                    # Note: We need to implement update_book_status in HardcoverClient properly if it's missing or use what's there
                    updated = await hc_client.update_book_status(match.book.id, "read")
                    if updated:
                        logger.info(f"Updated Hardcover status for '{title}'")
                        result["hardcover_updated"] = True
            except Exception as e:
                 logger.error(f"Failed Hardcover update for {title}: {e}")
                 
        return result
