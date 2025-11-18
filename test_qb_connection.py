"""Quick test of qBittorrent connection."""

import os
import sys
from dotenv import load_dotenv

# Force UTF-8 output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

try:
    import qbittorrentapi

    qb_host = os.getenv('QB_HOST', 'localhost')
    qb_port = os.getenv('QB_PORT', '8080')
    qb_username = os.getenv('QB_USERNAME', 'admin')
    qb_password = os.getenv('QB_PASSWORD', 'adminadmin')

    print(f"[*] Connecting to qBittorrent at {qb_host}:{qb_port}...")

    qbt_client = qbittorrentapi.Client(
        host=qb_host,
        port=qb_port,
        username=qb_username,
        password=qb_password
    )

    qbt_client.auth_log_in()

    print("[SUCCESS] Connection successful!")
    print(f"\nqBittorrent Info:")
    print(f"   Version: {qbt_client.app.version}")
    print(f"   Web API Version: {qbt_client.app.web_api_version}")

    # Get torrent stats
    torrents = qbt_client.torrents.info()
    print(f"\nTorrents:")
    print(f"   Total: {len(torrents)}")

    downloading = [t for t in torrents if t.state in ['downloading', 'stalledDL']]
    seeding = [t for t in torrents if t.state in ['uploading', 'stalledUP']]

    print(f"   Downloading: {len(downloading)}")
    print(f"   Seeding: {len(seeding)}")

    print("\n[SUCCESS] Ready to add audiobook torrents!")

except ImportError:
    print("[ERROR] qbittorrent-api not installed")
    print("Install with: pip install qbittorrent-api")
except Exception as e:
    print(f"[ERROR] Connection failed: {e}")
    print("\nTroubleshooting:")
    print(f"   - Check that qBittorrent is running")
    print(f"   - Verify Web UI is enabled: Tools -> Options -> Web UI")
    print(f"   - Check credentials in .env file")
    print(f"   - Try accessing http://{qb_host}:{qb_port} in browser")
