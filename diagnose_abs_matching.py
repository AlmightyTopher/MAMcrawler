import asyncio
import json
import os
import sys
import html
import logging
from dotenv import load_dotenv
from difflib import SequenceMatcher

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.integrations.abs_client import AudiobookshelfClient

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Matcher")

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

async def diagnose_matching():
    url = os.getenv("ABS_URL")
    token = os.getenv("ABS_TOKEN")
    
    with open("goodreads_books_dump.json", "r") as f:
        books = json.load(f)
        
    # Helper to check read status
    def is_read(book):
        s = book['shelves']
        if not s: 
            # If shelves empty, assume read? (Or unclassified)
            # Default to Read if not to-read/currently-reading
            return True
        
        # Collect all terms
        terms = []
        if isinstance(s, list):
            for item in s:
                if isinstance(item, str): terms.append(item)
                if isinstance(item, dict): terms.append(item.get('term', ''))
        else:
            terms.append(str(s))
            
        # Check exclusion
        if 'to-read' in terms: return False
        if 'currently-reading' in terms: return False
        
        return True

    # Filter for READ books
    read_books = [b for b in books if is_read(b)]
    print(f"Total READ books to match: {len(read_books)}")
    
    async with AudiobookshelfClient(url, token) as client:
        success = 0
        failed = 0
        
        for book in read_books:
            raw_title = book['title']
            author = book['author']
            
            # Unescape
            title = html.unescape(raw_title)
            author = html.unescape(author)
            
            print(f"\nScanning: {title} by {author}")
            
            match = await find_book_in_abs(client, title, author)
            
            if match:
                print(f"✅ MATCH FOUND: {match['media']['metadata']['title']} (ID: {match['id']})")
                success += 1
            else:
                print(f"❌ FAILED to match.")
                failed += 1
                
        print(f"\n--------------------------------")
        print(f"Diagnosis Complete.")
        print(f"Matched: {success}")
        print(f"Failed:  {failed}")
        print(f"Match Rate: {success/len(read_books)*100:.1f}%")

async def find_book_in_abs(client, title, author):
    # Strategy 1: Exact Title Search
    clean_title = title.split('(')[0].strip() # Remove " (Series #1)"
    
    # Try searching full clean title
    res = await search_and_verify(client, clean_title, author)
    if res: return res
    
    # Strategy 2: Split by Colon (Subtitle removal)
    if ':' in clean_title:
        short_title = clean_title.split(':')[0].strip()
        print(f"   -> Retrying with short title: '{short_title}'")
        res = await search_and_verify(client, short_title, author)
        if res: return res

    # Strategy 3: Search by Author (and fuzzy match title)
    print(f"   -> Retrying search by Author: '{author}'")
    res = await search_by_author_and_verify(client, author, clean_title)
    if res: return res

    return None

async def search_and_verify(client, query, target_author):
    results = await client.search_books(query, limit=5)
    if not results: return None
    
    # Check author fuzzy
    for item in results:
        meta = item.get('media', {}).get('metadata', {})
        item_author = meta.get('authorName', '')
        
        # Check Author Similarity
        if similarity(target_author, item_author) > 0.6 or target_author.lower() in item_author.lower():
            return item
            
    return None

async def search_by_author_and_verify(client, author, target_title):
    # Search for Author
    results = await client.search_books(author, limit=20)
    if not results: return None
    
    best_match = None
    best_score = 0
    
    for item in results:
        meta = item.get('media', {}).get('metadata', {})
        item_title = meta.get('title', '')
        
        # Compare Titles
        score = similarity(target_title, item_title)
        
        # Bonus if author matches perfectly
        item_author = meta.get('authorName', '')
        if author.lower() in item_author.lower():
            score += 0.1
            
        if score > 0.6 and score > best_score:
            best_match = item
            best_score = score
            
    if best_match:
        print(f"      (Found via Author search: {best_match['media']['metadata']['title']} - Score: {best_score:.2f})")
        return best_match
        
    return None

if __name__ == "__main__":
    try:
        asyncio.run(diagnose_matching())
    except KeyboardInterrupt:
        pass
