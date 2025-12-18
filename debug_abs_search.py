import asyncio
import os
import logging
from dotenv import load_dotenv
from backend.integrations.abs_client import AudiobookshelfClient

load_dotenv()
logging.basicConfig(level=logging.INFO)

async def debug_search():
    abs_url = os.getenv("ABS_URL")
    abs_token = os.getenv("ABS_TOKEN")
    
    print(f"Connecting to {abs_url}...")
    async with AudiobookshelfClient(abs_url, abs_token) as client:
        # Check libraries
        libs = await client.get_libraries()
        print(f"Found {len(libs)} libraries:")
        for lib in libs:
            print(f" - {lib['name']} (ID: {lib['id']})")
            
        # Search
        query = "Dungeon Crawler Carl"
        print(f"\nSearching for '{query}'...")
        results = await client.search_books(query)
        print(f"Found {len(results)} matches.")
        for book in results:
            print(f" - {book['media']['metadata']['title']} (ID: {book['id']})")

if __name__ == "__main__":
    asyncio.run(debug_search())
