import asyncio
import json
import os
import sys
from datetime import datetime

# Add current dir to path
sys.path.append(os.getcwd())

async def debug_data():
    print("Debugging Data Sources...")
    
    # 1. Check MAM Stats Cache
    print("\n[1] MAM Stats Cache (mam_stats.json):")
    if os.path.exists("mam_stats.json"):
        with open("mam_stats.json", "r") as f:
            stats = json.load(f)
            print(json.dumps(stats, indent=2))
    else:
        print("  File not found.")

    # 2. Check qBittorrent Direct
    print("\n[2] qBittorrent Direct Fetch:")
    try:
        from qbittorrent_session_client import QBittorrentSessionClient
        
        qb_host = os.getenv('QB_HOST', 'http://localhost')
        qb_port = os.getenv('QB_PORT', '8080')
        qb_user = os.getenv('QB_USERNAME', 'admin')
        qb_pass = os.getenv('QB_PASSWORD', '')
        
        qb_url = f"{qb_host}:{qb_port}" if not qb_host.endswith(qb_port) else qb_host
        print(f"  Connecting to {qb_url}...")
        
        client = QBittorrentSessionClient(qb_url, qb_user, qb_pass, timeout=5)
        if client.login():
            torrents = client.get_torrents()
            print(f"  Total Torrents: {len(torrents)}")
            
            # Filter for active
            active = [t for t in torrents if 'dl' in t.get('state', '').lower() or t.get('progress', 0) < 1.0]
            print(f"  Active/Incomplete: {len(active)}")
            
            for i, t in enumerate(active[:5]):
                print(f"    [{i}] Name: {t.get('name')}")
                print(f"        State: {t.get('state')}")
                print(f"        Size: {t.get('size')} (formatted: {format_size(t.get('size', 0))})")
                print(f"        Progress: {t.get('progress')}")
                print(f"        DL Speed: {t.get('dlspeed')}")
        else:
            print("  Login failed.")
            
    except Exception as e:
        print(f"  qBit Error: {e}")

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(debug_data())
