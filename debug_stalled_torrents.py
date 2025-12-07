import os
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugStalled")

load_dotenv()

try:
    import qbittorrentapi
except ImportError:
    print("Installing qbittorrentapi...")
    import subprocess
    subprocess.check_call(["pip", "install", "qbittorrent-api"])
    import qbittorrentapi

def debug_stalled():
    host = os.getenv('QB_HOST', 'http://localhost')
    port = os.getenv('QB_PORT', '8080')
    username = os.getenv('QB_USERNAME', 'admin')
    password = os.getenv('QB_PASSWORD', '')
    
    # Handle full URL in host
    if not host.startswith('http'):
        host = f'http://{host}'
    
    # If port is not in host, append it
    if str(port) not in host:
        host = f"{host}:{port}"
        
    print(f"Connecting to qBittorrent at {host}...")
    
    try:
        qbt = qbittorrentapi.Client(
            host=host,
            username=username,
            password=password
        )
        qbt.auth_log_in()
        print(f"✓ Connected (Version: {qbt.app.version})")
        
        # Get all torrents
        torrents = qbt.torrents_info(status_filter='stalled_downloading')
        print(f"\nFound {len(torrents)} stalled downloads.")
        
        if not torrents:
            # Check all torrents just in case
            torrents = qbt.torrents_info()
            print(f"Checking all {len(torrents)} torrents for issues...")
            
        for t in torrents[:5]: # Check first 5
            print(f"\n--- Torrent: {t.name[:50]}... ---")
            print(f"State: {t.state}")
            print(f"Progress: {t.progress * 100:.1f}%")
            print(f"Seeds: {t.num_seeds} (Peers: {t.num_leechs})")
            print(f"Download Speed: {t.dlspeed}")
            
            # Check Trackers
            trackers = qbt.torrents_trackers(t.hash)
            print("Trackers:")
            for tr in trackers:
                print(f"  - {tr.url}")
                print(f"    Status: {tr.status} (Msg: {tr.msg})")
                print(f"    Seeds: {tr.num_seeds} | Peers: {tr.num_peers}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_stalled()
