"""
VPN Manager for WireGuard.
Handles installation and uninstallation of WireGuard tunnels on Windows.
"""

import subprocess
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class VPNManager:
    """
    Manages WireGuard tunnels using the wireguard.exe CLI.
    """

    def __init__(self, wireguard_path: str = r"C:\Program Files\WireGuard\wireguard.exe"):
        self.wireguard_path = wireguard_path
        if not os.path.exists(self.wireguard_path):
            logger.warning(f"WireGuard executable not found at {self.wireguard_path}")

    def install_tunnel(self, config_path: str) -> bool:
        """
        Install and start a WireGuard tunnel service.
        
        Args:
            config_path: Absolute path to the .conf file.
            
        Returns:
            True if successful, False otherwise.
        """
        if not os.path.exists(config_path):
            logger.error(f"Config file not found: {config_path}")
            return False

        try:
            logger.info(f"Installing tunnel from {config_path}...")
            # wireguard.exe /installtunnelservice <path>
            result = subprocess.run(
                [self.wireguard_path, "/installtunnelservice", config_path],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Tunnel installed successfully: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            # Check if it failed because it already exists (common case)
            if "Service already exists" in e.stderr:
                logger.info("Tunnel service already exists.")
                return True
            logger.error(f"Failed to install tunnel: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error installing tunnel: {e}")
            return False

    def uninstall_tunnel(self, tunnel_name: str) -> bool:
        """
        Stop and uninstall a WireGuard tunnel service.
        
        Args:
            tunnel_name: Name of the tunnel (filename without extension).
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            logger.info(f"Uninstalling tunnel: {tunnel_name}...")
            # wireguard.exe /uninstalltunnelservice <name>
            result = subprocess.run(
                [self.wireguard_path, "/uninstalltunnelservice", tunnel_name],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Tunnel uninstalled successfully: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to uninstall tunnel: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uninstalling tunnel: {e}")
            return False

    def get_tunnel_status(self, tunnel_name: str) -> str:
        """
        Check if the tunnel service is running (via sc query).
        """
        service_name = f"WireGuardTunnel${tunnel_name}"
        try:
            result = subprocess.run(
                ["sc", "query", service_name],
                capture_output=True,
                text=True
            )
            if "RUNNING" in result.stdout:
                return "RUNNING"
            elif "STOPPED" in result.stdout:
                return "STOPPED"
            else:
                return "UNKNOWN"
        except Exception:
            return "UNKNOWN"
