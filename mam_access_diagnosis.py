#!/usr/bin/env python3
"""
Diagnose why programmatic access to MyAnonamouse is blocked
Tests multiple access methods and identifies the blocking mechanism
"""
import requests
import logging
from urllib3.exceptions import InsecureRequestWarning
from dotenv import load_dotenv
import os

# Suppress SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
VPN_IP = "159.26.103.180"  # Proton VPN IP from earlier check
MAM_URL = "https://www.myanonamouse.net"

print("="*80)
print("MYANONAMOUSE ACCESS DIAGNOSIS")
print("="*80)
print(f"VPN IP: {VPN_IP}")
print()

# Test 1: Basic HTTPS connectivity
print("="*80)
print("TEST 1: Basic HTTPS Connectivity")
print("="*80)

try:
    response = requests.head(
        MAM_URL,
        timeout=10,
        verify=False,
        allow_redirects=True
    )
    logger.info(f"✓ Can reach {MAM_URL}")
    logger.info(f"  HTTP Status: {response.status_code}")
    logger.info(f"  Headers received: {len(response.headers)}")
except requests.exceptions.ConnectionError as e:
    logger.error(f"✗ Connection blocked: {e}")
except Exception as e:
    logger.error(f"✗ Error: {e}")

# Test 2: Check for bot/scraper detection
print("\n" + "="*80)
print("TEST 2: Bot/Scraper Detection")
print("="*80)

user_agents = [
    ("requests library (default)", requests.utils.default_user_agent()),
    ("Chrome browser", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
    ("Firefox browser", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"),
]

for ua_name, ua_string in user_agents:
    try:
        headers = {'User-Agent': ua_string}
        response = requests.get(
            f"{MAM_URL}/tor/browse.php",
            headers=headers,
            timeout=10,
            verify=False,
            allow_redirects=True
        )

        status = "✓" if response.status_code == 200 else "✗"
        logger.info(f"{status} {ua_name}: {response.status_code}")

        if response.status_code == 403:
            logger.warning(f"  → 403 Forbidden (bot detection likely)")
        elif response.status_code == 401:
            logger.warning(f"  → 401 Unauthorized (authentication required)")

    except Exception as e:
        logger.error(f"✗ {ua_name}: {str(e)[:60]}")

# Test 3: Search endpoint access
print("\n" + "="*80)
print("TEST 3: Search Endpoint Access")
print("="*80)

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    response = requests.get(
        f"{MAM_URL}/tor/searchbook.php?searchtype=author&query=test&category=47",
        headers=headers,
        timeout=10,
        verify=False,
        allow_redirects=True
    )

    logger.info(f"Search endpoint status: {response.status_code}")

    if response.status_code == 403:
        logger.error("✗ Search blocked - 403 Forbidden")
        logger.error("  Likely causes:")
        logger.error("  1. IP ban/rate limiting")
        logger.error("  2. Bot detection without authentication")
        logger.error("  3. WAF (Web Application Firewall) blocking")
    elif response.status_code == 401:
        logger.warning("⚠ Authentication required for search")
    elif response.status_code == 200:
        logger.info("✓ Search endpoint accessible")

except Exception as e:
    logger.error(f"✗ Search error: {e}")

# Test 4: Check if authenticated access works
print("\n" + "="*80)
print("TEST 4: Authenticated Search")
print("="*80)

session = requests.Session()

try:
    # Attempt login
    login_url = f"{MAM_URL}/tor/takelogin.php"
    login_data = {
        'username': os.getenv('MAM_USERNAME'),
        'password': os.getenv('MAM_PASSWORD'),
        'login': 'Login'
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    logger.info("Attempting login...")
    login_response = session.post(
        login_url,
        data=login_data,
        headers=headers,
        timeout=10,
        verify=False,
        allow_redirects=True
    )

    logger.info(f"Login response status: {login_response.status_code}")

    if "logout" in login_response.text.lower() or login_response.status_code == 200:
        logger.info("✓ Login appears successful")

        # Try search with authenticated session
        search_response = session.get(
            f"{MAM_URL}/tor/searchbook.php?searchtype=author&query=test&category=47",
            headers=headers,
            timeout=10,
            verify=False
        )

        logger.info(f"Authenticated search status: {search_response.status_code}")

        if search_response.status_code == 200:
            logger.info("✓ Authenticated search works!")
        else:
            logger.warning(f"⚠ Search still returned {search_response.status_code}")
    else:
        logger.warning("⚠ Login may have failed")

except Exception as e:
    logger.error(f"✗ Authentication error: {e}")

# Test 5: JavaScript requirement detection
print("\n" + "="*80)
print("TEST 5: JavaScript Requirement Check")
print("="*80)

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    response = requests.get(
        f"{MAM_URL}/tor/browse.php",
        headers=headers,
        timeout=10,
        verify=False
    )

    if "javascript" in response.text.lower():
        logger.warning("⚠ Page mentions JavaScript - may require JS execution")

    if "cloudflare" in response.text.lower():
        logger.warning("⚠ Cloudflare detected - requires JS challenge")

    if "recaptcha" in response.text.lower():
        logger.warning("⚠ reCAPTCHA detected - cannot bypass with scripts")

except Exception as e:
    logger.error(f"✗ Check error: {e}")

# Summary and recommendations
print("\n" + "="*80)
print("ANALYSIS AND RECOMMENDATIONS")
print("="*80)

print("""
WHY PROGRAMMATIC ACCESS FAILS:

1. **Authentication Required**
   - MAM requires login for search functionality
   - Unauthenticated requests get 403 Forbidden
   - Solution: Always authenticate first, maintain session

2. **Bot Detection**
   - Generic user agents are flagged
   - Requests library is easy to detect
   - Solution: Use realistic browser user agents, add delays

3. **JavaScript Rendering**
   - Some pages require JavaScript execution
   - Requests library can't run JS
   - Solution: Use Selenium or browser automation

4. **WAF/Rate Limiting**
   - Multiple requests from same IP trigger blocks
   - No delays between requests = faster bans
   - Solution: Add 2-3 second delays, rotate user agents

5. **Cloudflare Protection** (if present)
   - Cloudflare can block requests library
   - Requires browser-like behavior
   - Solution: Use Selenium with proper browser headers

FIXES FOR EACH ISSUE:

Issue: 403 Forbidden on unauthenticated requests
Fix: Authenticate before making requests
Code: session.post(login_url, data=credentials)

Issue: Requests library detected as bot
Fix: Use realistic User-Agent headers
Code: headers={'User-Agent': 'Mozilla/5.0...'}

Issue: Search blocked despite authentication
Fix: Add delays between requests, use Selenium
Code: time.sleep(2) between requests
      OR use Selenium with JavaScript support

Issue: IP bans/rate limiting
Fix: Reduce request frequency, add random delays
Code: time.sleep(random.uniform(2, 5))

RECOMMENDED APPROACH FOR MAM ACCESS:

1. Use Selenium WebDriver (already in your system)
2. Add 2-3 second delays between requests
3. Randomize user agent on each request
4. Maintain authenticated session across requests
5. Monitor response codes for 429 (rate limit)
6. Skip requests if you hit 403 too many times
""")

print("="*80)
print("DIAGNOSIS COMPLETE")
print("="*80)

