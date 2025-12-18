import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.integrations.hardcover_client import HardcoverClient
from backend.integrations.google_books_client import GoogleBooksClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugResolution")

load_dotenv()

async def debug_resolution():
    token = os.getenv("HARDCOVER_TOKEN")
    gb_key = os.getenv("GOOGLE_BOOKS_API_KEY")
    
    title = "Dungeon Crawler Carl"
    author = "Matt Dinniman"
    
    print(f"\n--- Debugging Resolution for: {title} by {author} ---\n")
    
    # 1. Test Google Books extraction directly
    print("1. Querying Google Books...")
    async with GoogleBooksClient(api_key=gb_key) as gb:
        metadata = await gb.search_and_extract(title, author)
        print(f"   Result: {metadata}")
        if metadata:
            isbn13 = metadata.get("isbn_13")
            isbn10 = metadata.get("isbn_10")
            print(f"   ISBN-13: {isbn13}")
            print(f"   ISBN-10: {isbn10}")
        else:
            print("   No Google Books result.")
            
    # 2. Test Hardcover Resolution Flow
    print("\n2. Querying Hardcover (Full Flow)...")
    async with HardcoverClient(token) as hc:
        res = await hc.resolve_book(title, author)
        print(f"\n   Resolution Result: Success={res.success}")
        print(f"   Method: {res.resolution_method}")
        print(f"   Confidence: {res.confidence}")
        if res.book:
            print(f"   Book ID: {res.book.id}")
            print(f"   Book Title: {res.book.title}")
        else:
            print(f"   Note: {res.note}")
            
    # 3. Test Hardcover ISBN Search Explicitly (if GB found one)
    if metadata and (metadata.get("isbn_13") or metadata.get("isbn_10")):
        isbn_to_test = metadata.get("isbn_13") or metadata.get("isbn_10")
        print(f"\n3. Testing Hardcover ISBN Search Explicitly with {isbn_to_test}...")
        async with HardcoverClient(token) as hc:
             # Manually inspect the graphql query result for ISBN
             # We reuse client method
             res = await hc.resolve_by_isbn(isbn_to_test)
             print(f"   Result: Success={res.success}")
             if res.success and res.book:
                 print(f"   Book ID: {res.book.id}")
                 # Test Update Status
                 print(f"\n4. Testing Update Status for Book {res.book.id} -> Read...")
                 updated = await hc.update_book_status(res.book.id, "read")
                 print(f"   Update Result: {updated}")
             
             if not res.success:
                 print(f"   Note: {res.note}")

if __name__ == "__main__":
    asyncio.run(debug_resolution())
