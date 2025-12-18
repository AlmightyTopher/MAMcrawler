import asyncio
import os
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.integrations.abs_client import AudiobookshelfClient

load_dotenv()

async def monitor_progress():
    url = os.getenv("ABS_URL")
    token = os.getenv("ABS_TOKEN")
    
    print("Connecting to Audiobookshelf to monitor sync progress...")
    print("-------------------------------------------------------")
    
    last_count = 0
    
    async with AudiobookshelfClient(url, token) as client:
        # Find User ID
        users = await client.users.get_users()
        topher = next((u for u in users['users'] if u['username'] == 'TopherGutbrod'), None)
        if not topher:
            print("User TopherGutbrod not found!")
            return

        user_id = topher['id']
        
        while True:
            try:
                # Get fresh user data
                user_data = await client.users.get_user(user_id)
                progress = user_data.get("mediaProgress", [])
                
                # Filter finished
                finished_items = [p for p in progress if p.get("isFinished")]
                count = len(finished_items)
                
                # Sort by lastUpdate to find the most recent
                finished_items.sort(key=lambda x: x.get("lastUpdate", 0), reverse=True)
                
                latest_title = "None"
                if finished_items:
                    latest = finished_items[0]
                    # We need to fetch item to get title? Or is it in progress? 
                    # Progress usually has limited data. 
                    # We'll rely on the count mostly, and maybe try to fetch title if changed.
                    
                    if count > last_count or last_count == 0:
                        # Fetch title for the newest one
                        try:
                            item = await client._request("GET", f"/api/items/{latest['mediaItemId']}")
                            latest_title = item.get("media", {}).get("metadata", {}).get("title", "Unknown")
                        except:
                            latest_title = f"Item {latest['mediaItemId']}"
                
                if count != last_count:
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] FINISHED BOOKS: {count} (+{count - last_count}) | Latest: {latest_title}")
                    last_count = count
                else:
                    # Optional: Print heartbeat or just wait
                    # print(".", end="", flush=True) 
                    pass

                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Error checking progress: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(monitor_progress())
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
