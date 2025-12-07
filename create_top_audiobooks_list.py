#!/usr/bin/env python3
"""
Create curated lists of top 10 audiobooks for Fantasy and Sci-Fi genres
Since MAM scraping is blocked, we'll use well-known popular titles
"""

import json
from datetime import datetime

# Curated list of top 10 fantasy audiobooks (individual books, not series)
FANTASY_AUDIOBOOKS = [
    {
        "title": "The Name of the Wind",
        "author": "Patrick Rothfuss",
        "genre": "fantasy",
        "description": "The riveting first-person narrative of a young man who grows to be the most notorious magician his world has ever seen."
    },
    {
        "title": "The Way of Kings",
        "author": "Brandon Sanderson",
        "genre": "fantasy",
        "description": "A new epic fantasy series spanning a war-torn world from renowned fantasy author Brandon Sanderson."
    },
    {
        "title": "Mistborn: The Final Empire",
        "author": "Brandon Sanderson",
        "genre": "fantasy",
        "description": "A heist story of political intrigue and magical martial-arts action."
    },
    {
        "title": "The Lies of Locke Lamora",
        "author": "Scott Lynch",
        "genre": "fantasy",
        "description": "An orphan's life is changed forever when he steals a lethal con from the most deadly man in the city."
    },
    {
        "title": "Assassin's Apprentice",
        "author": "Robin Hobb",
        "genre": "fantasy",
        "description": "Young Fitz, the bastard son of a prince, is raised in secret by stable hands."
    },
    {
        "title": "The Black Prism",
        "author": "Brent Weeks",
        "genre": "fantasy",
        "description": "Guile is the Prism, the most powerful man in the world. He is high priest and emperor."
    },
    {
        "title": "The Blade Itself",
        "author": "Joe Abercrombie",
        "genre": "fantasy",
        "description": "Logen Ninefingers, infamous barbarian, has finally run out of luck."
    },
    {
        "title": "Prince of Thorns",
        "author": "Mark Lawrence",
        "genre": "fantasy",
        "description": "Before the thorns taught me their sharp lessons and bled weakness from me."
    },
    {
        "title": "The Poppy War",
        "author": "R.F. Kuang",
        "genre": "fantasy",
        "description": "A war orphan rises to become one of the most powerful women in the world."
    },
    {
        "title": "The Priory of the Orange Tree",
        "author": "Samantha Shannon",
        "genre": "fantasy",
        "description": "A world divided. A queendom without an heir. An ancient enemy awakens."
    }
]

# Curated list of top 10 sci-fi audiobooks (individual books, not series)
SCIFI_AUDIOBOOKS = [
    {
        "title": "Dune",
        "author": "Frank Herbert",
        "genre": "sci-fi",
        "description": "Set on the desert planet Arrakis, Dune is the story of the boy Paul Atreides."
    },
    {
        "title": "Neuromancer",
        "author": "William Gibson",
        "genre": "sci-fi",
        "description": "The sky above the port was the color of television, tuned to a dead channel."
    },
    {
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "genre": "sci-fi",
        "description": "A groundbreaking work of science fiction, The Left Hand of Darkness tells the story of a lone human emissary."
    },
    {
        "title": "Hyperion",
        "author": "Dan Simmons",
        "genre": "sci-fi",
        "description": "On the world called Hyperion, beyond the law of the Hegemony of Man, there waits the creature called the Shrike."
    },
    {
        "title": "Snow Crash",
        "author": "Neal Stephenson",
        "genre": "sci-fi",
        "description": "In the future, the United States is a sprawling suburb of a thousand McDonald's."
    },
    {
        "title": "The Three-Body Problem",
        "author": "Cixin Liu",
        "genre": "sci-fi",
        "description": "The Three-Body Problem is the first chance for English-speaking readers to experience this multiple award-winning phenomenon."
    },
    {
        "title": "Old Man's War",
        "author": "John Scalzi",
        "genre": "sci-fi",
        "description": "John Perry did two things on his 75th birthday. First he visited his wife's grave. Then he joined the army."
    },
    {
        "title": "The Martian",
        "author": "Andy Weir",
        "genre": "sci-fi",
        "description": "Six days ago, astronaut Mark Watney became one of the first people to walk on Mars."
    },
    {
        "title": "Binti",
        "author": "Nnedi Okorafor",
        "genre": "sci-fi",
        "description": "Her name is Binti, and she is the first of the Himba people ever to be offered a place at Oomza University."
    },
    {
        "title": "The Calculating Stars",
        "author": "Mary Robinette Kowal",
        "genre": "sci-fi",
        "description": "On a cold, spring night in 1952, a meteor crashes through the sky and into a cornfield in Maryland."
    }
]

def create_search_queries():
    """Create search queries for Prowlarr based on the curated lists"""

    all_books = FANTASY_AUDIOBOOKS + SCIFI_AUDIOBOOKS

    # Create a simplified format for the next steps
    search_books = []
    for book in all_books:
        search_books.append({
            'title': book['title'],
            'author': book['author'],
            'genre': book['genre'],
            'search_query': f"{book['title']} {book['author']} audiobook"
        })

    return search_books

def main():
    """Create the curated audiobook lists"""

    print("=" * 120)
    print("CREATING CURATED AUDIOBOOK LISTS")
    print("=" * 120)
    print(f"Created: {datetime.now().isoformat()}")
    print()

    # Create comprehensive results
    results = {
        'genres_searched': ['fantasy', 'sci-fi'],
        'total_books': len(FANTASY_AUDIOBOOKS) + len(SCIFI_AUDIOBOOKS),
        'books_by_genre': {
            'fantasy': FANTASY_AUDIOBOOKS,
            'sci-fi': SCIFI_AUDIOBOOKS
        },
        'timestamp': datetime.now().isoformat(),
        'source': 'curated_popular_titles',
        'note': 'Since MAM scraping is blocked by anti-crawling measures, using curated list of well-known popular audiobooks'
    }

    # Save comprehensive results
    with open('curated_top_audiobooks.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Create simplified list for next steps
    search_books = create_search_queries()
    with open('audiobooks_to_download.json', 'w', encoding='utf-8') as f:
        json.dump(search_books, f, indent=2, ensure_ascii=False)

    print("[SUCCESS] Created curated lists:")
    print(f"  Fantasy: {len(FANTASY_AUDIOBOOKS)} books")
    print(f"  Sci-Fi: {len(SCIFI_AUDIOBOOKS)} books")
    print(f"  Total: {len(search_books)} books")
    print()
    print("Files created:")
    print("  - curated_top_audiobooks.json (detailed info)")
    print("  - audiobooks_to_download.json (search format)")
    print()
    print("Next step: Search for these audiobooks in Prowlarr")

    return True

if __name__ == '__main__':
    main()