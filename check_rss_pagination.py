import feedparser
import logging

RSS_URL = "https://www.goodreads.com/review/list_rss/169104812?key=ZuC5jVSloRJK8oleoINvhV10kV_Qx6Hsa38BiLViW2MEEgz3&shelf=%23ALL%23"

logging.basicConfig(level=logging.INFO)

def check_pages():
    for page in range(1, 5):
        url = f"{RSS_URL}&page={page}"
        print(f"Checking Page {page}...")
        feed = feedparser.parse(url)
        print(f"Page {page}: {len(feed.entries)} entries")
        if not feed.entries:
            break

if __name__ == "__main__":
    check_pages()
