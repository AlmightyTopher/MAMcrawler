import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.integrations.hardcover_user_service import HardcoverUserService

import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

load_dotenv()

async def auto_sync_topher():
    token = os.getenv("HARDCOVER_TOKEN")
    if not token:
        print("Error: HARDCOVER_TOKEN not found in .env")
        return

    abs_url = os.getenv("ABS_URL")
    abs_token = os.getenv("ABS_TOKEN")
    
    service = HardcoverUserService(abs_url, abs_token)
    
    print("Registering TopherGutbrod...")
    # Register/Update mapping
    res = await service.register_user_async("TopherGutbrod", token)
    
    if res['success']:
        print("Registration successful.")
        print("Starting Sync...")
        # Sync just this user
        async with service.abs_client:
            # Fetch real ID
            users_resp = await service.abs_client.users.get_users()
            target_user = next((u for u in users_resp['users'] if u['username'] == 'TopherGutbrod'), None)
            
            if not target_user:
                print("Could not find TopherGutbrod in ABS users.")
                return

            # Debug: Print first progress item
            full_user = await service.abs_client.users.get_user(target_user['id'])
            progress = full_user.get("mediaProgress", [])
            print(f"Found {len(progress)} progress items.")
            if progress:
                print(f"Sample item keys: {progress[0].keys()}")
                import json
                print(json.dumps(progress[0], indent=2))

            sync_res = await service.sync_single_user({
                "abs_user_id": target_user['id'], 
                "abs_username": "TopherGutbrod",
                "hardcover_token": token
            })
            print("Sync Result:", sync_res)
    else:
        print(f"Registration failed: {res.get('error')}")

if __name__ == "__main__":
    asyncio.run(auto_sync_topher())
