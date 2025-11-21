import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
from bs4 import BeautifulSoup

PROXY = "socks5://127.0.0.1:8080"
URL = "https://www.myanonamouse.net/login.php"

async def inspect():
    connector = ProxyConnector.from_url(PROXY)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(URL) as resp:
            text = await resp.text()
            soup = BeautifulSoup(text, 'html.parser')
            forms = soup.find_all('form')
            for form in forms:
                print(f"Form action: {form.get('action')}")
                inputs = form.find_all('input')
                for i in inputs:
                    print(f"  Input: name={i.get('name')}, type={i.get('type')}, value={i.get('value')}")

if __name__ == "__main__":
    asyncio.run(inspect())
