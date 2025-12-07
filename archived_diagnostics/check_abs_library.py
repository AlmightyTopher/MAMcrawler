"""Check Audiobookshelf library contents"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

abs_url = os.getenv('ABS_URL')
abs_token = os.getenv('ABS_TOKEN')
headers = {'Authorization': f'Bearer {abs_token}'}

libs_response = requests.get(f'{abs_url}/api/libraries', headers=headers).json()
print(f'Libraries response type: {type(libs_response)}')
print(f'Libraries response: {libs_response}')

# Handle different response formats
if isinstance(libs_response, dict) and 'libraries' in libs_response:
    libs = libs_response['libraries']
elif isinstance(libs_response, list):
    libs = libs_response
else:
    libs = []

if libs:
    lib_id = libs[0]['id']
    print(f'Using library ID: {lib_id}')
    items = requests.get(f'{abs_url}/api/libraries/{lib_id}/items', headers=headers, params={'limit': 10}).json()
    print(f'Total items in library: {items.get("total", 0)}')
    print(f'First 10 titles:')
    for item in items.get('results', [])[:10]:
        title = item.get('media', {}).get('metadata', {}).get('title', 'Unknown')
        print(f'  - {title}')
else:
    print('No libraries found')
