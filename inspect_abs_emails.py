import asyncio
import os
from dotenv import load_dotenv
from backend.integrations.abs_client import AudiobookshelfClient

load_dotenv()

ABS_URL = os.getenv("ABS_URL", "http://localhost:13378")
ABS_TOKEN = os.getenv("ABS_TOKEN")

async def main():
    if not ABS_TOKEN:
        print("ABS_TOKEN not found")
        return

    client = AudiobookshelfClient(ABS_URL, ABS_TOKEN)
    try:
        data = await client.users.get_users()
        users = data.get("users", [])
        print(f"Found {len(users)} users:")
        for u in users:
            print(f"- {u['username']} (Email: {u.get('email', 'None')})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
