import asyncio
import os
import sys
import time
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.integrations.hardcover_user_service import HardcoverUserService
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables
load_dotenv()

ABS_URL = os.getenv("ABS_URL", "http://localhost:13378")
ABS_TOKEN = os.getenv("ABS_TOKEN")

# Known credentials map
KNOWN_CREDS = {
    "TopherGutbrod": {
        "email": "tophergutbrod@gmail.com",
        "password": "Tesl@ismy#1"
    }
}

async def get_abs_users():
    service = HardcoverUserService(ABS_URL, ABS_TOKEN)
    async with service.abs_client:
        resp = await service.abs_client.users.get_users()
        return resp.get("users", [])

def run_browser_registration(abs_user):
    username = abs_user['username']
    creds = KNOWN_CREDS.get(username)
    
    print(f"\n[Browser] Launching for user: {username}...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get("https://hardcover.app/login")
        
        if creds:
            print(f"[Browser] Auto-filling credentials for {username}...")
            wait = WebDriverWait(driver, 10)
            
            email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            email_input.clear()
            email_input.send_keys(creds['email'])
            
            pass_input = driver.find_element(By.NAME, "password")
            pass_input.clear()
            pass_input.send_keys(creds['password'])
            
            submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            print("[Browser] Login submitted...")
        else:
            print("[Instruction] Please LOG IN manually.")

        # Wait for token
        print("[Waiting] Waiting for successful login (token generation)...")
        token = None
        max_attempts = 300 
        attempts = 0
        
        while attempts < max_attempts:
            try:
                ls_keys = driver.execute_script("return Object.keys(localStorage);")
                for key in ls_keys:
                    if "token" in key.lower() or "auth" in key.lower():
                        val = driver.execute_script(f"return localStorage.getItem('{key}');")
                        if val and len(val) > 20: 
                            if val.startswith("{") and "access_token" in val:
                                js = json.loads(val)
                                token = js.get("access_token") or js.get("token")
                            elif val.startswith("ey"):
                                token = val
                            if token: break
            except:
                pass

            if not token:
                cookies = driver.get_cookies()
                for c in cookies:
                    if c['name'] in ['token', 'auth_token', 'access_token']:
                        token = c['value']
                        break
            
            if token:
                break
                
            time.sleep(1)
            attempts += 1
            
        if not token:
            print("[Error] Timed out waiting for login.")
            return None
            
        print(f"\n[Success] Token Extracted!")
        return token
        
    except Exception as e:
        print(f"[Error] Browser automation failed: {e}")
        return None
    finally:
        time.sleep(1)
        driver.quit()

async def main():
    print("==================================================")
    print("   AUTO-REGISTER HARDCOVER ACCOUNTS (CREDENTIALS)")
    print("==================================================")
    
    users = await get_abs_users()
    if not users:
        print("No users found.")
        return

    print("\nSelect user to auto-register:")
    for idx, u in enumerate(users):
        suffix = " (Creds Available!)" if u['username'] in KNOWN_CREDS else ""
        print(f"{idx+1}. {u['username']}{suffix}")
    
    choice = input("\nSelect # (or 'all'): ").strip()
    
    target_users = []
    if choice.lower() == 'all':
        target_users = users
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(users):
            target_users = [users[idx]]
    
    for u in target_users:
        print(f"\n--- Processing {u['username']} ---")
        token = run_browser_registration(u)
        
        if token:
            service = HardcoverUserService(ABS_URL, ABS_TOKEN)
            res = await service.register_user_async(u['username'], token)
            if res['success']:
                print(f"✅ Registered {u['username']} successfully.")
            else:
                print(f"❌ Registration failed: {res.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
