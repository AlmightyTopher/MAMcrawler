"""
Isolated test to debug qBittorrent authentication flow
Tests the exact same authentication sequence as ResilientClient
"""

import asyncio
import aiohttp
import re
import logging
from urllib.parse import urljoin

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_direct_http_connection():
    """Test 1: Direct HTTP connection to qBittorrent"""
    print("\n" + "="*80)
    print("TEST 1: Direct HTTP Connection (as we did before)")
    print("="*80)

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            url = "http://192.168.0.48:52095/"
            async with session.get(url, ssl=False) as resp:
                print(f"Status: {resp.status}")
                print(f"Headers: {dict(resp.headers)}")
                text = await resp.text()
                print(f"Response body length: {len(text)}")
                print("Result: [OK] ACCESSIBLE")
                return True
    except Exception as e:
        print(f"Error: {e}")
        print("Result: [FAIL] FAILED")
        return False


async def test_api_endpoint():
    """Test 2: Check if API endpoint is accessible"""
    print("\n" + "="*80)
    print("TEST 2: API Endpoint Accessibility")
    print("="*80)

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            api_url = "http://192.168.0.48:52095/api/v2/app/webapiVersion"
            print(f"Trying: {api_url}")
            async with session.get(api_url, ssl=False) as resp:
                print(f"Status: {resp.status}")
                text = await resp.text()
                print(f"Response: {text[:100]}")
                if resp.status == 200:
                    print("Result: [OK] API ACCESSIBLE")
                    return True
                else:
                    print(f"Result: [FAIL] HTTP {resp.status}")
                    return False
    except Exception as e:
        print(f"Error: {e}")
        print("Result: [FAIL] FAILED")
        return False


async def test_authentication_flow():
    """Test 3: Authentication flow (exact replica of ResilientClient)"""
    print("\n" + "="*80)
    print("TEST 3: Authentication Flow")
    print("="*80)

    url = "http://192.168.0.48:52095"
    username = "TopherGutbrod"
    password = "Tesl@ismy#1"

    try:
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30, connect=10, sock_read=20))

        # Step 1: Prepare login
        login_url = urljoin(url, "/api/v2/auth/login")
        print(f"\n1. Login URL: {login_url}")
        print(f"   Username: {username}")
        print(f"   Password: [REDACTED]")

        login_data = aiohttp.FormData()
        login_data.add_field('username', username)
        login_data.add_field('password', password)

        # Step 2: Attempt login
        print(f"\n2. Sending POST to {login_url}...")
        async with session.post(login_url, data=login_data, ssl=False) as resp:
            print(f"   Response Status: {resp.status}")
            print(f"   Response Headers: {dict(resp.headers)}")

            auth_text = await resp.text()
            print(f"   Response Body: '{auth_text}'")
            print(f"   Body stripped: '{auth_text.strip()}'")

            # Step 3: Check authentication result
            if resp.status != 200:
                print(f"   [FAIL] Login failed with HTTP {resp.status}")
                await session.close()
                return False

            if auth_text.strip() != 'Ok.':
                print(f"   [FAIL] Login failed: expected 'Ok.' but got '{auth_text.strip()}'")
                await session.close()
                return False

            print(f"   [OK] Login successful (got 'Ok.' response)")

            # Step 4: Extract SID
            print(f"\n3. Extracting SID cookie...")
            sid = None
            cookie_headers = []

            for header_name in resp.headers:
                if header_name.lower() == 'set-cookie':
                    cookie_val = resp.headers[header_name]
                    cookie_headers.append(cookie_val)
                    print(f"   Found Set-Cookie: {cookie_val[:80]}...")

                    match = re.search(r'SID=([^;]+)', cookie_val)
                    if match:
                        sid = match.group(1)
                        print(f"   [OK] Extracted SID: {sid[:20]}...")
                        break

            if not sid:
                print(f"   [FAIL] No SID found in {len(cookie_headers)} Set-Cookie headers")
                await session.close()
                return False

            print(f"\n4. [OK] Authentication successful, SID obtained")

        # Step 5: Try adding a torrent with the SID
        print(f"\n5. Testing torrent addition with SID...")
        add_url = urljoin(url, "/api/v2/torrents/add")
        test_magnet = "magnet:?xt=urn:btih:abc123&dn=Test"

        add_data = aiohttp.FormData()
        add_data.add_field('urls', test_magnet)
        add_data.add_field('paused', 'false')
        add_data.add_field('category', 'audiobooks')

        headers = {'Cookie': f'SID={sid}'}

        print(f"   URL: {add_url}")
        print(f"   Headers: {headers}")

        async with session.post(add_url, data=add_data, headers=headers, ssl=False) as resp:
            print(f"   Response Status: {resp.status}")
            response_text = await resp.text()
            print(f"   Response Body: '{response_text}'")

            if resp.status == 200 and response_text.strip() == 'Ok.':
                print(f"   [OK] Torrent addition successful")
            else:
                print(f"   Note: Status {resp.status}, body: {response_text}")

        await session.close()
        print(f"\n[OK] Authentication flow completed successfully")
        return True

    except Exception as e:
        print(f"[FAIL] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_real_resilient_client():
    """Test 4: Use actual ResilientClient"""
    print("\n" + "="*80)
    print("TEST 4: ResilientQBittorrentClient")
    print("="*80)

    try:
        from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient

        async with ResilientQBittorrentClient(
            primary_url="http://192.168.0.48:52095",
            secondary_url="http://localhost:52095",
            username="TopherGutbrod",
            password="Tesl@ismy#1"
        ) as client:
            print("1. Performing health check...")
            health = await client.perform_health_check()
            print(f"   Health: {health}")

            print("\n2. Attempting to add test magnet...")
            test_magnet = "magnet:?xt=urn:btih:def456&dn=TestBook"
            successful, failed, queued = await client.add_torrents_with_fallback([test_magnet])

            print(f"   Successful: {len(successful)}")
            print(f"   Failed: {len(failed)}")
            print(f"   Queued: {len(queued)}")

            if successful:
                print("[OK] ResilientClient working!")
                return True
            else:
                print("[FAIL] ResilientClient failed")
                return False

    except Exception as e:
        print(f"[FAIL] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("qBITTORRENT AUTHENTICATION DEBUG - COMPREHENSIVE TEST SUITE")
    print("="*80)

    results = {
        'Direct HTTP': await test_direct_http_connection(),
        'API Endpoint': await test_api_endpoint(),
        'Auth Flow': await test_authentication_flow(),
        'ResilientClient': await test_with_real_resilient_client(),
    }

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name}: {status}")

    print("\nANALYSIS:")
    if results['Direct HTTP'] and results['API Endpoint']:
        print("- qBittorrent is accessible via HTTP")
        if results['Auth Flow']:
            print("- Authentication flow works in isolation")
            if not results['ResilientClient']:
                print("- Issue: ResilientClient code has a bug compared to isolated test")
        else:
            print("- Authentication itself is failing (credentials or endpoint issue)")
    else:
        print("- Network connectivity issue")


if __name__ == '__main__':
    asyncio.run(main())
