import os
import logging
import time
from dotenv import load_dotenv
import qbittorrentapi

load_dotenv()

def verify_tracker_status():
    host = os.getenv('QB_HOST', 'http://localhost')
    port = os.getenv('QB_PORT', '8080')
    username = os.getenv('QB_USERNAME', 'admin')
    password = os.getenv('QB_PASSWORD', '')
    
    if not host.startswith('http'):
        host = f'http://{host}'
    if str(port) not in host:
        host = f"{host}:{port}"
        
    try:
        qbt = qbittorrentapi.Client(host=host, username=username, password=password)
        qbt.auth_log_in()
        
        print(f"Connected to qBittorrent at {host}")
        
        # Get torrents that are completed
        torrents = qbt.torrents_info(status_filter='completed')
        if not torrents:
            torrents = qbt.torrents_info(status_filter='stalled_uploading')
            
        print(f"Checking {len(torrents)} completed/seeding torrents...")
        
        for t in torrents[:5]:
            print(f"\nTorrent: {t.name}")
            print(f"State: {t.state}")
            
            trackers = qbt.torrents_trackers(t.hash)
            for tr in trackers:
                if 'myanonamouse' in tr.url:
                    print(f"Tracker: {tr.url}")
                    print(f"Status: {tr.status} (2=Working, 1=Not Contacted, 0=Disabled)")
                    print(f"Message: {tr.msg}")
                    
                    if tr.status != 2:
                        print("⚠️ Tracker not working correctly. Attempting force re-announce...")
                        qbt.torrents_reannounce(torrent_hashes=[t.hash])
                        time.sleep(2)
                        # Check again
                        new_trackers = qbt.torrents_trackers(t.hash)
                        for nt in new_trackers:
                            if nt.url == tr.url:
                                print(f"New Status: {nt.status} - {nt.msg}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_tracker_status()
