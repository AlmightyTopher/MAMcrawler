import asyncio
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("HARDCOVER_TOKEN")

async def test_query(name, query):
    print(f"\nTesting {name}...")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"query": query}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post("https://api.hardcover.app/v1/graphql", json=payload) as resp:
                data = await resp.json()
                if "errors" in data:
                    print(f"FAILED: {data['errors'][0]['message']}")
                else:
                    print(f"SUCCESS: Found results")
                    import json
                    print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"ERROR: {e}")

async def main():
    # 1. Test featured_book_series_id
    q1 = """query { books(limit: 1) { id title featured_book_series_id } }"""
    await test_query("featured_book_series_id", q1)

    # 2. Test book_series structure
    q2 = """query { books(limit: 1) { id title book_series { series { name } position } } }"""
    await test_query("book_series structure", q2)

    # 3. Test contributions (verify)
    q3 = """query { books(limit: 1) { id title contributions { author { name } } } }"""
    await test_query("contributions", q3)

    # 4. Test series at root?
    q4 = """query { series(limit: 1) { id name } }"""
    await test_query("series root", q4)
    
    # 5. Test user_books
    q5 = """query { user_books(limit: 1) { id } }"""
    await test_query("user_books root", q5)

if __name__ == "__main__":
    asyncio.run(main())
