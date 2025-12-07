import os
import logging
from dotenv import load_dotenv
import qbittorrentapi

load_dotenv()

def fix_qbit_binding():
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
        
        print("Current Binding:", qbt.app.preferences.get('current_network_interface'))
        
        # Reset binding to listen on all interfaces
        print("Resetting network interface binding to ANY...")
        qbt.app.set_preferences({
            'current_network_interface': '',
            'current_interface_address': ''
        })
        
        print("✓ Settings updated.")
        print("New Binding:", qbt.app.preferences.get('current_network_interface'))
        
        print("\nAttempting to re-announce stalled torrents...")
        torrents = qbt.torrents_info(status_filter='stalled_downloading')
        if torrents:
            hashes = [t.hash for t in torrents]
            qbt.torrents_reannounce(torrent_hashes=hashes)
            print(f"✓ Re-announced {len(hashes)} torrents.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_qbit_binding()
