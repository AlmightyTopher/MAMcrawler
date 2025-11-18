import requests, json, statistics
from collections import Counter

PROVIDERS = {
 "google": "https://www.googleapis.com/books/v1/volumes?q={q}+inauthor:{a}",
 "goodreads": "http://localhost:5555/goodreads/search?query={q}&author={a}",
 "kindle": "http://localhost:5555/kindle/us/search?query={q}&author={a}",
 "hardcover": "https://provider.vito0912.de/hardcover/en/book",
 "lubimyczytac": "http://localhost:3000/search?query={q}&author={a}",
 "audioteka": "http://localhost:3001/search?query={q}&author={a}"
}

HEADERS = {
 "google": {},
 "goodreads": {},
 "kindle": {},
 "hardcover": {"Authorization": "abs"},
 "lubimyczytac": {"Authorization": "00000"},
 "audioteka": {"Authorization": "00000"}
}

WEIGHTS = {"google":1.0,"hardcover":0.9,"goodreads":0.8,"kindle":0.8,"audioteka":0.7,"lubimyczytac":0.6}

FIELDS = ["title","author","series","year","isbn","cover","language","genres","description"]

def fetch(provider, title, author):
    try:
        url = PROVIDERS[provider].format(q=title.replace(" ","+"), a=author.replace(" ","+"))
        r = requests.get(url, headers=HEADERS.get(provider, {}), timeout=10)
        if r.ok:
            return normalize(provider, r.json())
    except: return {}
    return {}

def fetch_with_retry(provider, title, author):
    """Fetch with retry logic and fallback providers."""
    import time
    import logging

    # Primary provider with retries
    if provider == "google":
        retries = 0
        while retries < 2:
            try:
                data = fetch(provider, title, author)
                if data and not data.get("error") and data.get("status") == 200:
                    return data
                retries += 1
                logging.warning(f"Google attempt {retries} failed; retrying...")
                time.sleep(2)
            except Exception as e:
                retries += 1
                logging.warning(f"Google attempt {retries} exception: {e}; retrying...")
                time.sleep(2)

        # Google exhausted, try fallbacks
        logging.warning("Google exhausted; activating fallbacks")
        fallback_providers = ["hardcover", "goodreads", "kindle", "audioteka", "lubimyczytac"]
        for alt in fallback_providers:
            try:
                alt_data = fetch(alt, title, author)
                if alt_data:
                    logging.info(f"Fallback successful: {alt}")
                    return alt_data
            except Exception as e:
                logging.warning(f"Fallback {alt} failed: {e}")
                continue

    # For non-Google providers, just fetch normally
    return fetch(provider, title, author)

def normalize(provider, data):
    n = dict.fromkeys(FIELDS, None)
    d = data.get("items",[{}])[0].get("volumeInfo",{}) if provider=="google" else data
    n["title"] = d.get("title")
    n["author"] = d.get("author") or d.get("authors",[None])[0]
    n["series"] = d.get("series")
    n["year"] = d.get("year") or d.get("publishedDate", "")[:4]
    n["isbn"] = d.get("isbn") or next((x.get("identifier") for x in d.get("industryIdentifiers",[]) if "ISBN" in x.get("type","")), None)
    n["cover"] = d.get("cover") or d.get("imageLinks",{}).get("thumbnail")
    n["language"] = d.get("language")
    n["genres"] = d.get("genres") or d.get("categories")
    n["description"] = d.get("description")
    return n

def merge(results):
    merged, confidence = {}, {}
    for f in FIELDS:
        vals = [r[f] for r in results if r.get(f)]
        if not vals: continue
        top = Counter(vals).most_common(1)[0][0]
        merged[f] = top
        confidence[f] = round(min(1.0, sum(WEIGHTS[p] for p,r in results.items() if r.get(f)==top)/len(PROVIDERS)),2)
    merged["confidence"]=confidence
    return merged

def get_metadata(title, author):
    responses = {}
    for p in PROVIDERS: responses[p]=fetch_with_retry(p,title,author)
    return merge(responses)

if __name__=="__main__":
    print(json.dumps(get_metadata("Sparky the Dog","George Foreman"),indent=2))