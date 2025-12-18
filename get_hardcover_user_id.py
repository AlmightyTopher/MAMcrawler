import asyncio
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def get_me():
    token = os.getenv("HARDCOVER_TOKEN")
    url = "https://api.hardcover.app/v1/graphql"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    query = """
    query {
        me {
            id
            username
        }
    }
    """

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"query": query}, headers=headers) as resp:
            print(await resp.text())

if __name__ == "__main__":
    asyncio.run(get_me())
