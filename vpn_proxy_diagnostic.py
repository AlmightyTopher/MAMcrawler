#!/usr/bin/env python3
"""
VPN Proxy Diagnostic Tool
Tests ProtonVPN SOCKS5 proxy connectivity and configuration.
"""

import socket
import requests
import time
import subprocess
import sys
import os
from typing import Dict, List, Optional

def test_port_connectivity(host: str, port: int, timeout: float = 2.0) -> bool:
    """Test if a port is open and accepting connections."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error testing port {port}: {e}")
        return False

def test_proxy_functionality(proxy_url: str, test_url: str = "http://httpbin.org/ip") -> Dict:
    """Test if proxy is working by making a request."""
    result = {
        'working': False,
        'ip_address': None,
        'error': None
    }

    try:
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }

        response = requests.get(test_url, proxies=proxies, timeout=10)
        if response.status_code == 200:
            data = response.json()
            result['working'] = True
            result['ip_address'] = data.get('origin', 'Unknown')
        else:
            result['error'] = f"HTTP {response.status_code}"

    except requests.exceptions.ProxyError as e:
        result['error'] = f"Proxy error: {e}"
    except requests.exceptions.ConnectTimeout:
        result['error'] = "Connection timeout"
    except requests.exceptions.ConnectionError as e:
        result['error'] = f"Connection error: {e}"
    except Exception as e:
        result['error'] = f"Unexpected error: {e}"

    return result

def check_vpn_status() -> Dict:
    """Check if ProtonVPN is running and connected."""
    status = {
        'running': False,
        'connected': False,
        'processes': []
    }

    try:
        # Check for ProtonVPN processes
        if sys.platform == "win32":
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq protonvpn.exe'], capture_output=True, text=True)
            if 'protonvpn.exe' in result.stdout:
                status['running'] = True
                status['processes'].append('protonvpn.exe')

            # Also check for service
            result = subprocess.run(['sc', 'query', 'ProtonVPN Service'], capture_output=True, text=True)
            if 'RUNNING' in result.stdout:
                status['running'] = True
                status['processes'].append('ProtonVPN Service')

        else:
            # Linux/macOS
            result = subprocess.run(['pgrep', '-f', 'protonvpn'], capture_output=True, text=True)
            if result.returncode == 0:
                status['running'] = True
                status['processes'] = result.stdout.strip().split('\n')

    except Exception as e:
        print(f"Error checking VPN status: {e}")

    return status

def get_network_interfaces() -> List[Dict]:
    """Get network interface information."""
    interfaces = []

    try:
        if sys.platform == "win32":
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            # Parse Windows ipconfig output
            lines = result.stdout.split('\n')
            current_adapter = None

            for line in lines:
                line = line.strip()
                if 'adapter' in line.lower() and ':' in line:
                    current_adapter = line.split(':')[0].strip()
                elif current_adapter and ('IPv4 Address' in line or 'IP Address' in line):
                    ip = line.split(':')[-1].strip()
                    if ip and ip != '0.0.0.0':
                        interfaces.append({
                            'name': current_adapter,
                            'ip': ip,
                            'type': 'IPv4'
                        })

        else:
            # Linux/macOS - use ifconfig or ip
            try:
                result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
                lines = result.stdout.split('\n')
                current_interface = None

                for line in lines:
                    if line.startswith(' ') and 'inet ' in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            ip = parts[1].split('/')[0]
                            if ip != '127.0.0.1' and not ip.startswith('169.254'):
                                interfaces.append({
                                    'name': current_interface,
                                    'ip': ip,
                                    'type': 'IPv4'
                                })
                    elif line and not line.startswith(' '):
                        current_interface = line.split(':')[0]
            except:
                # Fallback to ifconfig
                result = subprocess.run(['ifconfig'], capture_output=True, text=True)
                # Basic parsing - could be improved

    except Exception as e:
        print(f"Error getting network interfaces: {e}")

    return interfaces

def main():
    print("=" * 60)
    print("VPN PROXY DIAGNOSTIC TOOL")
    print("=" * 60)

    # Check VPN status
    print("\n🔍 Checking ProtonVPN status...")
    vpn_status = check_vpn_status()
    if vpn_status['running']:
        print("✅ ProtonVPN appears to be running")
        print(f"   Processes: {', '.join(vpn_status['processes'])}")
    else:
        print("❌ ProtonVPN does not appear to be running")
        print("   Please start ProtonVPN and connect to a server")

    # Get network interfaces
    print("\n🔍 Checking network interfaces...")
    interfaces = get_network_interfaces()
    if interfaces:
        print("Network interfaces found:")
        for iface in interfaces:
            print(f"   {iface['name']}: {iface['ip']} ({iface['type']})")
    else:
        print("No network interfaces detected")

    # Test common proxy ports
    print("\n🔍 Testing proxy ports...")
    proxy_ports = [62410, 8080, 1080, 9050, 9150, 54674]

    working_ports = []
    for port in proxy_ports:
        if test_port_connectivity('127.0.0.1', port):
            print(f"✅ Port {port} is open")
            working_ports.append(port)
        else:
            print(f"❌ Port {port} is closed")

    if not working_ports:
        print("\n❌ No proxy ports are open!")
        print("This indicates:")
        print("   1. ProtonVPN is not connected")
        print("   2. Split tunneling is not enabled")
        print("   3. The proxy service is not running")
        return

    # Test proxy functionality
    print("\n🔍 Testing proxy functionality...")
    for port in working_ports:
        proxy_url = f"socks5://127.0.0.1:{port}"
        print(f"\nTesting {proxy_url}:")

        result = test_proxy_functionality(proxy_url)
        if result['working']:
            print(f"✅ Proxy is working! External IP: {result['ip_address']}")
        else:
            print(f"❌ Proxy test failed: {result['error']}")

    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    if not vpn_status['running']:
        print("1. Start ProtonVPN and connect to a server")
    else:
        print("1. ✅ ProtonVPN is running")

    if not working_ports:
        print("2. Enable Split Tunneling in ProtonVPN settings")
        print("   - Go to Settings → Advanced → Split Tunneling")
        print("   - Enable 'Split Tunneling'")
        print("   - Add your Python executable to 'Included Apps'")
        print("   - Add your terminal/command prompt to 'Included Apps'")
    else:
        print("2. ✅ Proxy ports are accessible")

    if working_ports:
        print("3. Test the dual scraper:")
        print(f"   venv\\Scripts\\python.exe dual_goodreads_scraper.py")
        print("   Look for '✅ Detected ProtonVPN SOCKS5 proxy' in the output")

    print("\n4. If issues persist:")
    print("   - Restart ProtonVPN")
    print("   - Disable and re-enable split tunneling")
    print("   - Check ProtonVPN logs for errors")
    print("   - Try a different VPN server")

if __name__ == "__main__":
    main()