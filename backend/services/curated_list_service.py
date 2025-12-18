
import logging
import re
from typing import List, Dict, Set
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from backend.config import get_settings
from backend.services.mam_selenium_service import MAMSeleniumService
from backend.integrations.prowlarr_client import ProwlarrClient
from backend.services.discovery_service import DiscoveryService

logger = logging.getLogger(__name__)
settings = get_settings()

class CuratedListService:
    """
    Service to fetch curated lists (e.g. Top 10 Fantasy) from MAM
    and ensure they exist in Prowlarr/qBittorrent.
    """

    def __init__(self):
        self.mam_service = MAMSeleniumService()
        self.discovery_service = DiscoveryService()

    async def scan_fantasy_top10(self) -> Dict[str, int]:
        """
        Scan Top 10 Fantasy Audiobooks from last 7 days on MAM
        and send missing ones to Prowlarr.
        """
        logger.info("Starting Curated List Scan: Top 10 Fantasy")
        stats = {
            "found": 0,
            "in_library": 0,
            "sent_to_prowlarr": 0,
            "errors": 0
        }

        try:
            # 1. Get Library Inventory
            # DiscoveryService has scan_library, but we need raw title set for check
            # For now, let's just use what's in the DB if possible, or scan
            # Actually DiscoveryService returns a report, let's trust it or implement simple inventory here
            # To match `fantasy_to_prowlarr.py` logic:
            library_result = await self.discovery_service.scan_library()
            library_files = set() 
            # scan_library returns dict with matches. 
            # We assume users have files in F:\Audiobookshelf\Books or similar.
            # `fantasy_to_prowlarr.py` scanned F:\Audiobookshelf\Books. 
            # We should probably trust the DB if Phase 3 is working.
            
            from backend.database import get_db_context
            from backend.models.book import Book
            
            with get_db_context() as db:
                books = db.query(Book).filter(Book.status == "active").all()
                library_titles = {b.title.lower().strip() for b in books}
                
            logger.info(f"Loaded {len(library_titles)} titles from DB library.")
            
            # 2. Scrape MAM
            results = await self._scrape_mam_fantasy()
            stats["found"] = len(results)
            
            # 3. Process Results
            missing_books = []
            for book in results:
                title = book['title']
                
                # Check fuzzy match
                is_present = False
                title_lower = title.lower()
                for lib_title in library_titles:
                    if lib_title in title_lower or title_lower in lib_title:
                         # Simple substring match improvement
                         if len(lib_title) > 5:
                             is_present = True
                             break
                
                if is_present:
                    stats["in_library"] += 1
                    logger.info(f"Skipping '{title}' (In Library)")
                    continue
                    
                missing_books.append(book)

            # 4. Send to Prowlarr
            if missing_books and settings.PROWLARR_API_KEY:
                async with ProwlarrClient(settings.PROWLARR_URL, settings.PROWLARR_API_KEY) as prowlarr:
                    for book in missing_books:
                        try:
                            logger.info(f"Sending '{book['title']}' to Prowlarr...")
                            # Prowlarr needs manual grab with download URL (which is torrent link here)
                            # The ProwlarrClient.add_release we added supports this.
                            # MAM link: https://www.myanonamouse.net/tor/download.php/tid/....
                            # We might need the full URL.
                            
                            # In `fantasy_to_prowlarr.py`, `link` was the torrent page URL or download link?
                            # It used `book['link']` which seemed to be the page URL.
                            # And `extract_magnet_links` also got `magnet`.
                            # If we have magnet, we can queue directly to QB? 
                            # But request was "Prowlarr Integration". 
                            # Prowlarr tracks history.
                            
                            # Let's prefer Magnet if available, else link.
                            download_url = book.get('magnet') or book.get('link')
                            
                            success = await prowlarr.add_release(book['title'], download_url)
                            if success:
                                stats["sent_to_prowlarr"] += 1
                            else:
                                stats["errors"] += 1
                        except Exception as e:
                            logger.error(f"Failed to send '{book['title']}': {e}")
                            stats["errors"] += 1
                            
        except Exception as e:
            logger.error(f"Curated Scan Failed: {e}", exc_info=True)
            raise

        return stats

    async def _scrape_mam_fantasy(self) -> List[Dict]:
        """Scrape Top Fantasy from MAM"""
        # Construct Search URL (Last 7 days, Fantasy Cat 41, Sort Snatched Desc)
        today = datetime.now()
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        
        url = (
            f"{self.mam_service.mam_url}/tor/browse.php?"
            f"&tor[srchIn][title]=true&tor[srchIn][author]=true&tor[srchIn][narrator]=true"
            f"&tor[searchType]=all&tor[searchIn]=torrents&tor[cat][]=41"
            f"&tor[startDate]={start_date}&tor[endDate]={end_date}"
            f"&tor[sortType]=snatchedDesc&tor[startNumber]=0"
        )
        
        html_source = self.mam_service.get_page_source(url)
        if not html_source:
             return []
             
        # Parse HTML (Logic ported from fantasy_to_prowlarr.py extract_magnet_links)
        soup = BeautifulSoup(html_source, 'html.parser')
        rows = soup.find_all('tr', id=re.compile('^tdr-'))
        
        results = []
        for row in rows[:20]: # Top 20
            try:
                title_elem = row.find('a', class_='torTitle')
                if not title_elem: continue
                
                title = title_elem.text.strip()
                href = title_elem['href']
                full_link = f"https://www.myanonamouse.net{href}" if href.startswith('/') else href
                
                # Find magnet
                magnet = None
                dl_link = row.find('a', href=re.compile(r'magnet:'))
                if dl_link:
                    magnet = dl_link['href']
                
                results.append({
                    'title': title,
                    'link': full_link,
                    'magnet': magnet
                })
            except Exception as e:
                logger.error(f"Error parsing row: {e}")
                
        return results
