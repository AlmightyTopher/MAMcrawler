import feedparser
import json
import logging
import time

RSS_URL = "https://www.goodreads.com/review/list_rss/169104812?key=ZuC5jVSloRJK8oleoINvhV10kV_Qx6Hsa38BiLViW2MEEgz3&shelf=%23ALL%23"

def fetch_all_books():
    all_entries = []
    page = 1
    while True:
        print(f"Fetching page {page}...")
        feed = feedparser.parse(f"{RSS_URL}&page={page}")
        if not feed.entries:
            break
        print(f"Found {len(feed.entries)} entries.")
        
        for entry in feed.entries:
            # Extract only needed fields
            book = {
                "title": entry.get('title'),
                "author": entry.get('author_name'),
                "isbn": entry.get('isbn'),
                "shelves": entry.get('user_shelves', ''),
                "book_id": entry.get('book_id')
            }
            all_entries.append(book)
        
        if len(feed.entries) < 100:
            break
        page += 1
        time.sleep(1)
        
    print(f"Total books fetched: {len(all_entries)}")
    with open("goodreads_books_dump.json", "w") as f:
        json.dump(all_entries, f, indent=2)

if __name__ == "__main__":
    fetch_all_books()
