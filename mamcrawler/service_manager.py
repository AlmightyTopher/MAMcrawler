import os
import time
import socket
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages auto-starting of required services."""
    
    def __init__(self):
        self.services = {
            'audiobookshelf': {
                'port': 13378,
                'exe': r"C:\Users\dogma\AppData\Local\Programs\Audiobookshelf\AudiobookshelfTray.exe",
                'name': "Audiobookshelf"
            },
            'qbittorrent': {
                'port': int(os.getenv('QB_PORT', 8080)),
                'exe': r"C:\Program Files\qBittorrent\qbittorrent.exe",
                'name': "qBittorrent"
            },
            'prowlarr': {
                'port': 9696,
                'exe': r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
                'name': "Docker Desktop (for Prowlarr)"
            }
        }

    def is_port_open(self, port: int, host: str = 'localhost') -> bool:
        """Check if a port is open."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                return s.connect_ex((host, port)) == 0
        except:
            return False

    def start_service(self, service_key: str):
        """Start a service if it's not running."""
        service = self.services.get(service_key)
        if not service:
            return

        if self.is_port_open(service['port']):
            logger.info(f"✓ {service['name']} is running.")
            return

        logger.info(f"⚠ {service['name']} not detected (Port {service['port']} closed). Launching...")
        exe_path = Path(service['exe'])
        
        if not exe_path.exists():
            logger.error(f"❌ Executable not found at {exe_path}")
            return

        try:
            # Use os.startfile for Windows GUI applications to detach completely
            if os.name == 'nt':
                os.startfile(str(exe_path))
            else:
                subprocess.Popen([str(exe_path)], start_new_session=True)
                
            logger.info(f"🚀 Launched {service['name']}. Waiting for startup...")
            
            # Wait loop (up to 30 seconds)
            # Docker might take longer, but we shouldn't block forever
            retries = 30
            if service_key == 'prowlarr':
                retries = 60 # Give Docker more time
                
            for _ in range(retries):
                if self.is_port_open(service['port']):
                    logger.info(f"✓ {service['name']} is now running.")
                    return
                time.sleep(1)
            
            logger.warning(f"⚠ {service['name']} launched but port {service['port']} is not yet open. Proceeding anyway.")
            
        except Exception as e:
            logger.error(f"❌ Failed to launch {service['name']}: {e}")

    def ensure_all_services(self):
        """Check and start all services."""
        logger.info("Checking required services...")
        for key in ['audiobookshelf', 'qbittorrent', 'prowlarr']:
            self.start_service(key)
