"""Test connectivity to required services"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
abs_url = os.getenv('ABS_URL', 'http://localhost:13378')

print('Testing qBittorrent...')
qb_ok = False
try:
    r = requests.get(f'{qb_url}api/v2/app/version', timeout=5)
    qb_ok = r.status_code == 200 or r.status_code == 401
    print(f'qBittorrent: {"OK" if qb_ok else "FAIL"}')
except Exception as e:
    print(f'qBittorrent: FAIL - {e}')

print('Testing Audiobookshelf...')
abs_ok = False
try:
    r = requests.get(f'{abs_url}/ping', timeout=5)
    abs_ok = r.status_code == 200
    print(f'Audiobookshelf: {"OK" if abs_ok else "FAIL"}')
except Exception as e:
    print(f'Audiobookshelf: FAIL - {e}')

if qb_ok and abs_ok:
    print('\nAll services are running!')
    exit(0)
else:
    print('\nSome services are not running!')
    exit(1)
