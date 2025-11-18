#!/usr/bin/env python3
"""
Simple VPN Proxy Test
Tests if ProtonVPN SOCKS5 proxy is working.
"""

import socket
import requests
import sys

def test_proxy(port):
    """Test if proxy port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False

def test_proxy_request(port):
    """Test if proxy works for HTTP requests."""
    try:
        proxies = {
            'http': f'socks5://127.0.0.1:{port}',
            'https': f'socks5://127.0.0.1:{port}'
        }
        response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('origin', 'Unknown')
        return None
    except Exception as e:
        return f"Error: {e}"

def main():
    print("VPN Proxy Test")
    print("=" * 30)

    # Test the port you mentioned
    port = 62410
    print(f"Testing port {port}...")

    if test_proxy(port):
        print(f"[+] Port {port} is open")
        print("Testing proxy functionality...")
        result = test_proxy_request(port)
        if result and not result.startswith("Error"):
            print(f"[+] Proxy working! External IP: {result}")
        else:
            print(f"[-] Proxy test failed: {result}")
    else:
        print(f"[-] Port {port} is closed")

    print("\nIf port is closed:")
    print("1. Start ProtonVPN")
    print("2. Enable Split Tunneling")
    print("3. Add your Python executable to 'Included Apps'")
    print("4. Restart the scraper")

if __name__ == "__main__":
    main()