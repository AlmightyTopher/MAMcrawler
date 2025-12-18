import asyncio
import os
import sys
import logging
from datetime import datetime
import feedparser
import html
import re
from difflib import SequenceMatcher
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.integrations.abs_client import AudiobookshelfClient
from backend.integrations.hardcover_client import HardcoverClient

# Configure logging to file for Dashboard compatibility
log_file = f"master_manager_goodreads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Force redirect full output to file
log_stream = open(log_file, 'a', encoding='utf-8', buffering=1)
sys.stdout = log_stream
sys.stderr = log_stream

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

RSS_URL = "https://www.goodreads.com/review/list_rss/169104812?key=ZuC5jVSloRJK8oleoINvhV10kV_Qx6Hsa38BiLViW2MEEgz3&shelf=%23ALL%23"

class GoodreadsSync:
    def __init__(self):
        self.abs_url = os.getenv("ABS_URL")
        self.abs_token = os.getenv("ABS_TOKEN")
        self.hardcover_token = os.getenv("HARDCOVER_TOKEN")
        
        self.abs_client = AudiobookshelfClient(self.abs_url, self.abs_token) if self.abs_token else None
        self.rss_url = RSS_URL

    async def _build_abs_library_cache(self, user_id):
        """Brute force: Fetch ALL items to ensure we don't miss anything due to API search quirks."""
        logger.info("BRUTE FORCE: Downloading entire Audiobookshelf library index...")
        try:
            # Get default library ID
            libs = await self.abs_client.get_libraries()
            if not libs:
                logger.error("No libraries found in ABS!")
                return
            
            lib_id = libs[0]['id'] # Use first library
            all_items = await self.abs_client.get_library_items(lib_id, limit=99999)
            
            logger.info(f"BRUTE FORCE: Indexed {len(all_items)} books from ABS local library.")
            
            for item in all_items:
                media = item.get('media', {})
                metadata = media.get('metadata', {})
                title = metadata.get('title', '')
                author = metadata.get('authorName', '')
                
                if title:
                    # Normalize for matching
                    clean_title = self._clean_string(title)
                    self.abs_cache.append({
                        'id': item['id'],
                        'title': title,
                        'clean_title': clean_title,
                        'author': author,
                        'clean_author': self._clean_string(author),
                        'duration': media.get('duration', 0),
                        'raw_item': item
                    })
        except Exception as e:
            logger.error(f"Failed to build brute force cache: {e}")

    def _clean_string(self, text):
        """Aggressive cleaning: lowercase, remove subtitles, remove punctuation."""
        if not text: return ""
        # Remove content in brackets/parentheses
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'\[.*?\]', '', text)
        # Remove special chars
        text = re.sub(r'[^\w\s]', '', text)
        # Normalize whitespace
        return " ".join(text.split()).lower()

    async def _brute_force_match(self, title, author):
        """Find best match in local cache."""
        clean_target_title = self._clean_string(title)
        clean_target_author = self._clean_string(author)
        
        matches = []
        
        # 1. Title contains match
        for item in self.abs_cache:
            score = 0
            # Exact match (High priority)
            if clean_target_title == item['clean_title']:
                score += 100
            # Fuzzy match (SequenceMatcher)
            else:
                ratio = SequenceMatcher(None, clean_target_title, item['clean_title']).ratio()
                if ratio > 0.85:
                    score += int(ratio * 90)
                # Substring match (Low priority, mainly for "Book X" vs "Title")
                elif clean_target_title in item['clean_title'] and len(clean_target_title) > 5:
                    score += 40 # Reduced from 80 to avoid matching "Book 1" to "Book 6"
            
            if score > 0:
                # Author penalty/bonus
                if clean_target_author and item['clean_author']:
                    if clean_target_author in item['clean_author']:
                        score += 30
                    elif SequenceMatcher(None, clean_target_author, item['clean_author']).ratio() > 0.8:
                        score += 20
                else:
                     # No author info? Risk.
                     pass

            matches.append((score, item))
        
        # Sort by score
        matches.sort(key=lambda x: x[0], reverse=True)
        
        # Threshold 80: Requires Exact (100) or High Fuzzy (85+) or Substring (40) + Author (30) + ??? 
        # Actually Substring (40) + Author (30) = 70. Fails. Good.
        # Exact (100) + Author (30) = 130. Pass.
        if matches and matches[0][0] >= 80:
            logger.info(f"BRUTE FORCE MATCH: '{title}' -> '{matches[0][1]['title']}' (Score: {matches[0][0]})")
            return matches[0][1]['raw_item']
        
        return None

    async def run(self):
        logger.info("Starting Goodreads Sync (Brute Force Mode)...")
        
        abs_token = os.getenv("ABS_TOKEN")
        abs_url = os.getenv("ABS_URL")
        hardcover_token = os.getenv("HARDCOVER_TOKEN")
        
        if not all([abs_token, abs_url, hardcover_token]):
            logger.critical("Missing credentials in .env")
            return

        async with AudiobookshelfClient(abs_url, abs_token) as abs_client:
            self.abs_client = abs_client
            
            # 0. Get User ID
            user_id = await self._get_abs_user_id("TopherGutbrod")
            if not user_id:
                logger.error("Could not find ABS User ID for 'TopherGutbrod'")
                return

            # 1. Build Brute Force Cache
            self.abs_cache = []
            await self._build_abs_library_cache(user_id)

            async with HardcoverClient(hardcover_token) as hc_client:
                # Pagination loop
                page = 1
                while True:
                    logger.info(f"Fetching RSS Page {page}...")
                    feed_url = f"{self.rss_url}&page={page}"
                    feed = await asyncio.to_thread(feedparser.parse, feed_url)
                    
                    if not feed or not feed.entries:
                        logger.info("No more entries found (or failed to fetch). Sync complete.")
                        break
                    
                    logger.info(f"Page {page}: Found {len(feed.entries)} books.")
                    
                    for entry in feed.entries:
                        try:
                            await self._process_book(entry, user_id, hc_client)
                        except Exception as e:
                            logger.error(f"Error processing book: {e}")
                        
                        # Respect rate limits for Hardcover/Google (Increased to 10s)
                        await asyncio.sleep(10)
                    
                    if len(feed.entries) < 100:
                        break
                    page += 1

    async def _get_abs_user_id(self, username):
        try:
            users_resp = await self.abs_client.users.get_users()
            for u in users_resp.get("users", []):
                if u["username"].lower() == username.lower():
                    return u["id"]
        except Exception as e:
            logger.error(f"Error fetching ABS users: {e}")
        return None

    async def _process_book(self, entry, abs_user_id, hc_client):
        title = html.unescape(entry.get('title', ''))
        author = html.unescape(entry.get('author_name', ''))
        isbn = entry.get('isbn')
        user_shelves = entry.get('user_shelves', '')
        
        # Aggressive author cleanup for "J.M.     Clarke"
        author = " ".join(author.split())
        
        logger.info(f"Processing '{title}' by {author}...")
        
        # Check if read
        is_read = False
        if entry.get('user_read_at'):
            is_read = True
        else:
            shelf_names = []
            if isinstance(user_shelves, list):
                for s in user_shelves:
                    if isinstance(s, dict):
                        shelf_names.append(s.get('term', ''))
                        shelf_names.append(s.get('label', ''))
                    else:
                        shelf_names.append(str(s))
            else:
                shelf_names.append(str(user_shelves))
            
            if 'to-read' in shelf_names:
                is_read = False
            elif 'currently-reading' in shelf_names:
                is_read = False
            else:
                is_read = True # Implicit read
                
            if 'read' in shelf_names: is_read = True
                
        if not is_read:
            return

        # --- ABS SYNC (BRUTE FORCE) ---
        found_item = await self._brute_force_match(title, author)
        if found_item:
            # Mark as read in ABS
            try:
                duration = found_item.get('media', {}).get('duration', 0)
                # Update progress to finished via ProgressManager
                await self.abs_client.progress.update_media_progress(
                    library_item_id=found_item['id'],
                    progress=1.0,
                    current_time=duration,
                    is_finished=True
                )
                logger.info(f"Marked '{title}' as READ in Audiobookshelf (Brute Force Match)")
            except Exception as e:
                logger.error(f"Failed to update ABS progress: {e}")
        else:
            logger.warning(f"Could not find '{title}' in ABS library (Local Cache search failed).")

        # --- HARDCOVER SYNC ---
        if hc_client:
            clean_title = title.split('(')[0].strip()
            await self._sync_to_hardcover(clean_title, author, isbn, hc_client)

    async def _sync_to_hardcover(self, title, author, isbn, hc_client):
        logger.info(f"Syncing to Hardcover: {title}")
        
        # Resolve
        match = await hc_client.resolve_book(title, author, isbn)
        if not match.success or not match.book:
            logger.warning(f"Could not resolve '{title}' on Hardcover.")
            return

        # Update Status
        if await hc_client.update_book_status(match.book.id, "read"):
            logger.info(f"Updated Hardcover status for '{match.book.title}'")

    async def _sync_to_abs(self, title, author, user_id):
        try:
            search_res = await self.abs_client.search_books(
                query=title,
                limit=5
            )
            
            found_item = None
            if search_res:
                for item in search_res:
                     media = item.get('media', {})
                     meta = media.get('metadata', {})
                     item_author = meta.get('authorName', '')
                     
                     if author.lower() in item_author.lower():
                         found_item = item
                         break
            
            if found_item:
                logger.info(f"Marking '{title}' as READ in ABS...")
                item_id = found_item['id']
                payload = {
                    "isFinished": True,
                    "currentTime": found_item.get('media', {}).get('duration', 0),
                    "progress": 1.0
                }
                await self.abs_client._request("PATCH", f"/api/me/progress/{item_id}", json=payload)
            else:
                logger.debug(f"Book '{title}' not found in ABS.")
                
        except Exception as e:
            logger.error(f"ABS Sync Error for {title}: {e}")

    async def _sync_to_hardcover(self, title, author, isbn, hc_client):
        # Try resolve
        logger.info(f"Syncing to Hardcover: {title}")
        match = await hc_client.resolve_book(title, author)
        
        if match.success and match.book:
             await hc_client.update_book_status(match.book.id, "read")
             logger.info(f"Updated Hardcover status for '{title}'")
        else:
             logger.warning(f"Could not resolve '{title}' on Hardcover.")

if __name__ == "__main__":
    syncer = GoodreadsSync()
    asyncio.run(syncer.run())
