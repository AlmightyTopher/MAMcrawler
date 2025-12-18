
import asyncio
import logging
import os
import sys
from mam_selenium_crawler import SeleniumMAMCrawler
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_search():
    load_dotenv()
    
    email = os.getenv('MAM_USERNAME')
    password = os.getenv('MAM_PASSWORD')
    qb_url = os.getenv('QB_HOST', 'http://localhost') + ':' + os.getenv('QB_PORT', '8080')
    qb_user = os.getenv('QB_USERNAME', 'admin')
    qb_pass = os.getenv('QB_PASSWORD', '')
    
    print(f"DEBUG: Connecting to {qb_url} as {qb_user}")
    
    crawler = SeleniumMAMCrawler(email, password, qb_url, qb_user, qb_pass, headless=True)
    
    print("DEBUG: Setting up crawler...")
    if not crawler.setup():
        print("ERROR: Setup failed")
        return

    print("DEBUG: Logging in...")
    if not crawler.login():
        print("ERROR: Login failed")
        print("DEBUG PAGE TITLE:", crawler.driver.title)
        print("DEBUG PAGE TEXT SNAPSHOT:", crawler.driver.find_element("tag name", "body").text[:500])
        return

    # Use a known popular book
    search_term = "Dungeon Crawler Carl"
    print(f"DEBUG: Searching for '{search_term}'...")
    
    result = crawler.search_mam(search_term)
    
    if result:
        print("SUCCESS: Found book!")
        print(result)
        
        # Try to queue it
        magnet = result.get('magnet')
        if magnet:
            print("DEBUG: Attempting to queue magnet...")
            try:
                crawler.qb_client.torrents_add(urls=magnet)
                print("SUCCESS: Queued to qBittorrent")
            except Exception as e:
                print(f"ERROR: Failed to queue: {e}")
        else:
            print("ERROR: No magnet link in result")
            
    else:
        print("FAILURE: No results found for known book.")
        # Save page source if possible? 
        # The crawler already saves 'mam_torrent_*.html' optionally, let's check current directory later.

    crawler.cleanup()

if __name__ == "__main__":
    asyncio.run(debug_search())
