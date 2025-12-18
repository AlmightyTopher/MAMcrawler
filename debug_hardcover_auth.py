import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.integrations.hardcover_client import HardcoverClient

logging.basicConfig(level=logging.DEBUG)
load_dotenv()

async def test_auth():
    token = os.getenv("HARDCOVER_TOKEN")
    print(f"Testing token: {token[:10]}...")
    
    async with HardcoverClient(token) as client:
        # Try get_me
        try:
            print("Fetching ME...")
            me = await client.get_me()
            print(f"ME: {me}")
        except Exception as e:
            print(f"ME Failed: {e}")

        # Try Resolve
        try:
            print("Resolving book 'The Way of Kings'...")
            res = await client.resolve_book("The Way of Kings", "Brandon Sanderson")
            print(f"Resolve Result: {res}")
        except Exception as e:
            print(f"Resolve Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth())
