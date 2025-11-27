#!/usr/bin/env python
"""
Test both mam_id values to see which one works
"""

import asyncio
from pathlib import Path
import urllib.parse
import aiohttp
from bs4 import BeautifulSoup

async def test_cookie(cookie_value, label):
    print(f"\nTesting: {label}")
    print(f"Cookie value: {cookie_value[:50]}...")
    print(f"Encoded length: {len(cookie_value)}")

    # Decode it
    decoded = urllib.parse.unquote(cookie_value)
    print(f"Decoded length: {len(decoded)}")
    print(f"Decoded value: {decoded[:50]}...")

    search_url = "https://www.myanonamouse.net/tor/browse.php?tor[searchstr]=test&tor[cat][]=13"

    async with aiohttp.ClientSession() as session:
        cookies = {'mam_id': decoded}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            async with session.get(search_url, cookies=cookies, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                html = await response.text()

                # Check if authenticated
                soup = BeautifulSoup(html, 'html.parser')
                title = soup.find('title')
                title_text = title.get_text() if title else "N/A"

                logout_link = soup.find('a', string=lambda x: x and 'logout' in x.lower())
                torrent_row = soup.find('tr', class_='torrentrow')

                print(f"Status: {response.status}")
                print(f"Page title: {title_text}")
                print(f"Logout link: {'YES' if logout_link else 'NO'}")
                print(f"Torrent rows: {'YES' if torrent_row else 'NO'}")

                if 'Login' not in title_text and logout_link:
                    print("  --> AUTHENTICATED!")
                    return True
                elif torrent_row:
                    print("  --> GOT RESULTS!")
                    return True
                else:
                    print("  --> Not authenticated")
                    return False
        except Exception as e:
            print(f"Error: {e}")
            return False

async def main():
    # Extract both mam_id values
    env_content = Path('.env').read_text()

    mam_ids = {}
    for line_num, line in enumerate(env_content.split('\n'), 1):
        if 'mam_id' in line and '=' in line and len(line.split('=')[1].strip()) > 50:
            raw_val = line.split('=')[1].strip().strip('\'"')
            label = f"Line {line_num} ({len(raw_val)} chars)"
            mam_ids[label] = raw_val

    print(f"Found {len(mam_ids)} mam_id values")
    print("=" * 80)

    results = {}
    for label, cookie in mam_ids.items():
        result = await test_cookie(cookie, label)
        results[label] = result

    print("\n" + "=" * 80)
    print("RESULTS:")
    for label, result in results.items():
        status = "SUCCESS" if result else "FAILED"
        print(f"{label}: {status}")

if __name__ == '__main__':
    asyncio.run(main())
