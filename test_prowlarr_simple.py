
import asyncio
import os
import logging
from dotenv import load_dotenv
from backend.integrations.prowlarr_client import ProwlarrClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_prowlarr():
    load_dotenv()
    
    url = os.getenv('PROWLARR_URL')
    api_key = os.getenv('PROWLARR_API_KEY')
    
    print(f"URL: {url}")
    print(f"API Key: {api_key[:4]}...{api_key[-4:]} (masked)")
    
    if not url or not api_key:
        print("ERROR: credentials missing from .env")
        return

    print("\n--- Testing Prowlarr Connection ---")
    async with ProwlarrClient(url, api_key) as client:
        try:
            # 1. Test System Status
            status = await client.get_system_status()
            print(f"✅ Connection Successful! Prowlarr Version: {status.get('version')}")
            
            # 2. Test Search (Audiobooks)
            search_query = "Dungeon Crawler Carl"
            print(f"\n--- Searching for '{search_query}' (NO CATEGORY FILTER) ---")
            results = await client.search(search_query)
            
            print(f"Found {len(results)} results.")
            
            if results:
                print("\nTop 3 Results:")
                for i, res in enumerate(results[:3]):
                    print(f"[{i+1}] Title: {res.get('title')}")
                    print(f"    Indexer: {res.get('indexer')}")
                    print(f"    Seeders: {res.get('seeders')}")
                    print(f"    Size: {res.get('size')}")
                    print(f"    InfoUrl: {res.get('infoUrl')}")
                    print(f"    Magnet: {res.get('magnetUrl') is not None}")
            else:
                print("⚠ No results found. Check Category IDs (3010) or Indexers.")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_prowlarr())
