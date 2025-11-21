import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

    
    session = requests.Session()
    session.proxies = {
        'http': PROXY,
        'https': PROXY
    }
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    print("Fetching login page...")
    resp = session.get(f"{URL}/login.php")
    soup = BeautifulSoup(resp.text, 'html.parser')
    token = soup.find('input', {'name': 't'}).get('value')
    print(f"Token: {token[:10]}...")

    # Try 1: Raw token, no unquote
    print("--- Attempt 1: Raw token ---")
    data = {
        "email": USERNAME,
        "password": PASSWORD,
        "t": token, # Raw
        "rememberMe": "yes",
        "login": "Log in!"
    }
    resp = session.post(f"{URL}/takelogin.php", data=data)
    if "logout" in resp.text.lower():
        print("Login SUCCESS!")
        return
    else:
        print("Login FAILED!")

    # Try 2: Unquoted token
    print("--- Attempt 2: Unquoted token ---")
    import urllib.parse
    token_decoded = urllib.parse.unquote(token)
    data["t"] = token_decoded
    resp = session.post(f"{URL}/takelogin.php", data=data)
    if "logout" in resp.text.lower():
        print("Login SUCCESS!")
        return
    else:
        print("Login FAILED!")

    # Try 3: Unquoted token, no 'login' field
    print("--- Attempt 3: No login field ---")
    del data["login"]
    resp = session.post(f"{URL}/takelogin.php", data=data)
    if "logout" in resp.text.lower():
        print("Login SUCCESS!")
        return
    else:
        print("Login FAILED!")

    # Try 4: Unquoted token, no rememberMe
    print("--- Attempt 4: No rememberMe ---")
    if "rememberMe" in data: del data["rememberMe"]
    resp = session.post(f"{URL}/takelogin.php", data=data)
    if "logout" in resp.text.lower():
        print("Login SUCCESS!")
        return
    else:
        print("Login FAILED!")
        
    # Try 5: Email field with actual email? (Can't guess it, but maybe USERNAME is email?)
    # If USERNAME is not email, maybe that's the issue.
    # But error "Required fields are missing" suggests structural issue.

if __name__ == "__main__":
    login()
