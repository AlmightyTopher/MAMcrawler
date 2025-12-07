import os
import logging
from dotenv import load_dotenv
import qbittorrentapi

load_dotenv()

def check_qbit_settings():
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
        
        prefs = qbt.app.preferences
        
        print("\n--- qBittorrent Network Settings ---")
        print(f"Proxy Type: {prefs.get('proxy_type')} (0=None, 1=HTTP, 2=SOCKS5)")
        print(f"Proxy IP: {prefs.get('proxy_ip')}")
        print(f"Proxy Port: {prefs.get('proxy_port')}")
        print(f"Proxy Peer Connections: {prefs.get('proxy_peer_connections')}")
        print(f"Force Proxy: {prefs.get('proxy_auth_enabled')}")
        
        print("\n--- Interface Binding ---")
        print(f"Network Interface: {prefs.get('current_interface_address')}")
        print(f"Bind Interface: {prefs.get('current_network_interface')}")
        
        print("\n--- Other Settings ---")
        print(f"Anonymous Mode: {prefs.get('anonymous_mode')}")
        print(f"DHT Enabled: {prefs.get('dht')}")
        print(f"PeX Enabled: {prefs.get('pex')}")
        print(f"LSD Enabled: {prefs.get('lsd')}")
        print(f"Encryption: {prefs.get('encryption')}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_qbit_settings()
