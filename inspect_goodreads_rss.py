import feedparser
import json

RSS_URL = "https://www.goodreads.com/review/list_rss/169104812?key=ZuC5jVSloRJK8oleoINvhV10kV_Qx6Hsa38BiLViW2MEEgz3&shelf=%23ALL%23"

def inspect_rss():
    print(f"Parsing RSS: {RSS_URL}")
    feed = feedparser.parse(RSS_URL)
    
    print(f"Feed Title: {feed.feed.get('title', 'Unknown')}")
    print(f"Entries Found: {len(feed.entries)}")
    
    if feed.entries:
        entry = feed.entries[0]
        print("\n--- Sample Entry ---")
        # Print keys available
        print(f"Keys: {entry.keys()}")
        
        # Details
        import json
        # Convert to standard dict to avoid feedparser specific types issue
        print(json.dumps(entry, indent=2, default=str))

if __name__ == "__main__":
    inspect_rss()
