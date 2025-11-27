import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from dotenv import load_dotenv
import os

load_dotenv()

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

login_data = {'email': os.getenv('MAM_USERNAME'), 'password': os.getenv('MAM_PASSWORD'), 'login': 'Login'}
session.post("https://www.myanonamouse.net/login.php", data=login_data, timeout=30, allow_redirects=True)
print(f"Login: OK, Cookies: {list(session.cookies.keys())}")

search_url = "https://www.myanonamouse.net/tor/browse.php?tor[searchstr]=Sanderson%20Stormlight&tor[cat][]=13"
response = session.get(search_url, timeout=30)
print(f"Search: {response.status_code}, Length: {len(response.text)}")

soup = BeautifulSoup(response.text, 'html.parser')
rows = soup.find_all('tr', class_=lambda x: x and 'torrent' in str(x).lower())
print(f"Torrent rows found: {len(rows)}")

torrent_links = soup.find_all('a', href=lambda x: x and '/t/' in str(x))
print(f"Torrent links (/t/): {len(torrent_links)}")

if torrent_links:
    for i, link in enumerate(torrent_links[:3]):
        print(f"  {i+1}. {link.get_text(strip=True)[:60]}")

with open('search_debug.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
print("Saved search_debug.html")
