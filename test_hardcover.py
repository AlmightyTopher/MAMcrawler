import requests
import json

# Test Hardcover API
url = "https://api.hardcover.app/v1/graphql"
token = "eyJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJIYXJkY292ZXIiLCJ2ZXJzaW9uIjoiOCIsImp0aSI6IjAzNTBjMTE5LWQ2MjItNDQ3NS05YWQxLWE4MzYzNTBmOGZmYyIsImFwcGxpY2F0aW9uSWQiOjIsInN1YiI6IjQ1OTA5IiwiYXVkIjoiMSIsImlkIjoiNDU5MDkiLCJsb2dnZWRJbiI6dHJ1ZSwiaWF0IjoxNzYzNjcxNzI0LCJleHAiOjE3OTUyMDc3MjQsImh0dHBzOi8vaGFzdXJhLmlvL2p3dC9jbGFpbXMiOnsieC1oYXN1cmEtYWxsb3dlZC1yb2xlcyI6WyJ1c2VyIl0sIngtaGFzdXJhLWRlZmF1bHQtcm9sZSI6InVzZXIiLCJ4LWhhc3VyYS1yb2xlIjoidXNlciIsIlgtaGFzdXJhLXVzZXItaWQiOiI0NTkwOSJ9LCJ1c2VyIjp7ImlkIjo0NTkwOX19.jMFEQ9U04SqSWWYkhl-lPDiu3JuN_gCBeruY7tHQc0I"

# Test 1: Check authentication with 'me' query
print("Test 1: Authentication check (with Bearer)...")
headers_bearer = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

query_me = """
query {
  me {
    id
    username
  }
}
"""

response = requests.post(url, headers=headers_bearer, json={'query': query_me})
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
print()

# Test 2: Search for a book
print("Test 2: Book search with exact match...")
query_books = """
query SearchBooks($title: String!) {
  books(where: {title: {_eq: $title}}, limit: 5) {
    title
    description
    release_date
    rating
    contributions {
      author {
        name
      }
    }
    images {
      url
    }
  }
}
"""

variables = {"title": "The Name of the Wind"}

response = requests.post(url, headers=headers_bearer, json={'query': query_books, 'variables': variables})
print(f"Status: {response.status_code}")
result = response.json()
print(f"Response: {json.dumps(result, indent=2)[:500]}...")

if 'data' in result and result['data'].get('books'):
    books = result['data']['books']
    print(f"\n✅ Found {len(books)} books!")
    for book in books:
        authors = [c['author']['name'] for c in book.get('contributions', []) if c.get('author')]
        print(f"  - {book['title']} by {', '.join(authors)}")
