#!/usr/bin/env python
"""
Refresh MAM Session Cookies - Uses .env credentials to log in and get fresh cookies
"""

import requests
import json
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

# Load environment
env_file = Path('.env')
config = {}
if env_file.exists():
    for line in env_file.read_text().split('\n'):
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            config[k.strip()] = v.strip().strip('\'"')

MAM_USERNAME = config.get('MAM_USERNAME', '').strip('\'"')
MAM_PASSWORD = config.get('MAM_PASSWORD', '').strip('\'"')

logger.info("="*80)
logger.info("MAM SESSION COOKIE REFRESH")
logger.info("="*80)
logger.info(f"Username: {MAM_USERNAME}")

# Create session and log in
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

# Step 1: Get login page (to establish initial session)
logger.info("\nStep 1: Visiting login page...")
response = session.get('https://www.myanonamouse.net/login.php', timeout=15)
logger.info(f"  Status: {response.status_code}")

# Step 2: Submit login form
logger.info("\nStep 2: Submitting login credentials...")
login_data = {
    'username': MAM_USERNAME,
    'password': MAM_PASSWORD,
    'login': 'Login'
}

response = session.post(
    'https://www.myanonamouse.net/takelogin.php',
    data=login_data,
    timeout=15,
    allow_redirects=True
)

logger.info(f"  Status: {response.status_code}")

# Step 3: Verify login - check for session cookies
logger.info("\nStep 3: Verifying authentication...")

# Check if we have any session cookie (lid is the new format)
if session.cookies.get('lid') or session.cookies.get('uid') or session.cookies.get('mam_id'):
    logger.info("  SUCCESS: Session cookie received!")
else:
    logger.error("  FAILED: No session cookie received")
    exit(1)

# Try accessing authenticated page
response = session.get('https://www.myanonamouse.net/tor/search.php', timeout=15)
if response.status_code == 200:
    logger.info("  Authenticated page accessible")

# Step 4: Extract cookies
logger.info("\nStep 4: Extracting session cookies...")

# MAM uses different cookie names depending on login method
uid = session.cookies.get('uid')
mam_id = session.cookies.get('mam_id')
lid = session.cookies.get('lid')

logger.info(f"  Available cookies: {list(session.cookies.keys())}")

if lid:
    logger.info(f"  Found 'lid' cookie (new session format)")
    # 'lid' is the session token, we can use it as mam_id
    mam_id = lid
    # uid might not be available with this method, let's derive or use placeholder
    uid = session.cookies.get('uid', 'UNKNOWN')

if mam_id:
    logger.info(f"  UID: {uid if uid != 'UNKNOWN' else 'Not provided by MAM'}")
    logger.info(f"  Session Token: {mam_id[:50]}...")

    # Step 5: Update .env file
    logger.info("\nStep 5: Updating .env file...")

    env_content = env_file.read_text()

    # Update or add uid
    if 'uid = ' in env_content or 'uid=' in env_content:
        lines = env_content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('uid'):
                lines[i] = f'uid = {uid}'
                break
        env_content = '\n'.join(lines)
    else:
        env_content += f'\nuid = {uid}\n'

    # Update or add mam_id
    if 'mam_id = ' in env_content or 'mam_id=' in env_content:
        lines = env_content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('mam_id'):
                lines[i] = f'mam_id = {mam_id}'
                break
        env_content = '\n'.join(lines)
    else:
        env_content += f'mam_id = {mam_id}\n'

    env_file.write_text(env_content)
    logger.info("  SUCCESS: .env file updated!")

    logger.info("\n" + "="*80)
    logger.info("FRESH COOKIES OBTAINED")
    logger.info("="*80)
    logger.info("\nYou can now run Phase 1 executor:")
    logger.info("  python PHASE1_SIMPLE_EXECUTOR.py")

else:
    logger.error("  FAILED: Could not extract cookies")
    logger.error("  Cookies in session:", session.cookies.get_dict())
    exit(1)
