import requests
import json
import urllib.parse

def search_itunes_audiobook(title, author):
    print(f"Searching iTunes for: {title} by {author}")
    
    # Construct query
    query = f"{title} {author}"
    encoded_query = urllib.parse.quote(query)
    url = f"https://itunes.apple.com/search?term={encoded_query}&media=audiobook&entity=audiobook&limit=1"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['resultCount'] > 0:
            item = data['results'][0]
            print("\n✅ FOUND MATCH:")
            print(f"  Title: {item.get('collectionName')}")
            print(f"  Author: {item.get('artistName')}")
            desc = item.get('description', '')
            narrator = desc.split('Narrated by ')[1].split('\n')[0] if 'Narrated by ' in desc else 'Unknown'
            print(f"  Narrator: {narrator}")
            print(f"  Release Date: {item.get('releaseDate')}")
            print(f"  Genre: {item.get('primaryGenreName')}")
            print(f"  Description: {item.get('description')[:100]}...")
            return True
        else:
            print(f"\n❌ No results found for: {title}")
            return False
            
    except Exception as e:
        print(f"\n⚠ Error: {e}")
        return False

if __name__ == "__main__":
    # Test with some known books and some that might be in your library
    test_books = [
        ("The Name of the Wind", "Patrick Rothfuss"),
        ("Project Hail Mary", "Andy Weir"),
        ("Dungeon Crawler Carl", "Matt Dinniman"),
        ("He Who Fights with Monsters", "Shirtaloon")
    ]
    
    print("Testing iTunes Audiobook API...")
    print("-" * 50)
    
    success_count = 0
    for title, author in test_books:
        if search_itunes_audiobook(title, author):
            success_count += 1
        print("-" * 50)
        
    print(f"\nSuccess rate: {success_count}/{len(test_books)}")
