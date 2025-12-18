import asyncio
import os
import sys
from getpass import getpass
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.integrations.hardcover_user_service import HardcoverUserService

# Load environment variables
load_dotenv()

ABS_URL = os.getenv("ABS_URL", "http://localhost:13378")
ABS_TOKEN = os.getenv("ABS_TOKEN")

if not ABS_TOKEN:
    print("Error: ABS_TOKEN not found in .env file")
    sys.exit(1)

service = HardcoverUserService(ABS_URL, ABS_TOKEN)

async def list_abs_users():
    """Fetch and list all users from ABS"""
    print("\nFetching AudiobookShelf users...")
    async with service.abs_client:
        try:
            resp = await service.abs_client.users.get_users()
            users = resp.get("users", [])
            return users
        except Exception as e:
            print(f"Error fetching users: {e}")
            return []

async def main():
    print("==================================================")
    print("   HARDCOVER.APP USER SYNCHRONIZATION MANAGER")
    print("==================================================")
    
    while True:
        print("\nOptions:")
        print("1. List Registered Sync Users")
        print("2. Register New User for Sync")
        print("3. Sync All Users Now")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            registered = await service.get_registered_users()
            if not registered:
                print("\nNo users registered for sync yet.")
            else:
                print(f"\nRegistered Users ({len(registered)}):")
                print(f"{'ABS Username':<20} | {'Hardcover Token (Masked)':<25} | {'Last Synced'}")
                print("-" * 70)
                for u in registered:
                    token_mask = u['hardcover_token'][:5] + "..." + u['hardcover_token'][-5:]
                    print(f"{u['abs_username']:<20} | {token_mask:<25} | {u['last_synced_at']}")

        elif choice == "2":
            abs_users = await list_abs_users()
            if not abs_users:
                print("No users found in AudiobookShelf.")
                continue
                
            print("\nAvailable AudiobookShelf Users:")
            for idx, u in enumerate(abs_users):
                print(f"{idx+1}. {u['username']} (Type: {u['type']})")
                
            u_idx = input("\nSelect user number to register: ").strip()
            if not u_idx.isdigit() or int(u_idx) < 1 or int(u_idx) > len(abs_users):
                print("Invalid selection.")
                continue
                
            selected_user = abs_users[int(u_idx)-1]
            username = selected_user['username']
            
            print(f"\n--- Registering {username} ---")
            print("Instructions to get Hardcover Token:")
            print("1. Log into https://hardcover.app")
            print("2. Open Developer Tools (F12) -> Application/Storage -> Cookies or Local Storage")
            print("3. Look for 'token' or check Network tab for 'Authorization: Bearer <token>'")
            print("   (Or use their API settings if available)")
            
            token = getpass(f"Enter Hardcover Bearer Token for {username}: ").strip()
            
            if not token:
                print("Registration cancelled.")
                continue
                
            print("Verifying...")
            result = await service.register_user_async(username, token)
            
            if result["success"]:
                print(f"SUCCESS! Linked {username} to Hardcover user '{result['hardcover_user']}'")
            else:
                print(f"FAILED: {result.get('error')}")

        elif choice == "3":
            print("\nStarting synchronization...")
            results = await service.sync_all_users()
            print("\nSync Results:")
            for res in results:
                status = res['status']
                user = res['user']
                if status == 'success':
                    stats = res['stats']
                    print(f"✅ {user}: Synced {stats['synced']}, Skipped {stats['skipped']}, Failed {stats['failed']}")
                else:
                    print(f"❌ {user}: {res.get('error')}")

        elif choice == "4":
            print("Goodbye.")
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
