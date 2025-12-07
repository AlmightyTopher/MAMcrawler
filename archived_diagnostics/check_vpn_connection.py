#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick VPN connection checker
"""

import subprocess
import sys
import socket

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("ProtonVPN Connection Status Check")
print("=" * 70)
print()

# Check processes
print("[1] ProtonVPN Processes:")
print("-" * 70)
try:
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ProtonVPN*'],
                          capture_output=True, text=True, timeout=5)
    lines = [l for l in result.stdout.split('\n') if 'ProtonVPN' in l]
    if lines:
        for line in lines:
            print(f"  ✅ {line.strip()}")
    else:
        print("  ❌ No ProtonVPN processes found")
except Exception as e:
    print(f"  ❌ Error: {e}")

print()

# Check network interfaces
print("[2] Checking Network Adapters:")
print("-" * 70)
try:
    result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=5)

    # Look for ProtonVPN/WireGuard/TAP adapters
    in_vpn_section = False
    vpn_found = False

    for line in result.stdout.split('\n'):
        line_lower = line.lower()
        if 'adapter' in line_lower and ('proton' in line_lower or 'wireguard' in line_lower or 'tap' in line_lower or 'vpn' in line_lower):
            print(f"  ✅ Found: {line.strip()}")
            vpn_found = True
            in_vpn_section = True
        elif in_vpn_section and 'ipv4' in line_lower:
            print(f"     {line.strip()}")
            in_vpn_section = False

    if not vpn_found:
        print("  ❌ No VPN network adapter found")
        print("     This usually means ProtonVPN is NOT connected to a server")
except Exception as e:
    print(f"  ❌ Error: {e}")

print()

# Scan for SOCKS ports more aggressively
print("[3] Comprehensive Port Scan (SOCKS5 proxies):")
print("-" * 70)

# Extended port list
all_ports = list(range(1080, 1090)) + list(range(8080, 8090)) + list(range(9050, 9060)) + [54674, 62410, 3128, 8888]

found_ports = []
for port in all_ports:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.3)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        if result == 0:
            found_ports.append(port)
    except:
        pass

if found_ports:
    print(f"  ✅ Found {len(found_ports)} open port(s):")
    for port in found_ports:
        print(f"     • Port {port}")
else:
    print("  ❌ No SOCKS proxy ports detected")

print()
print("=" * 70)
print("DIAGNOSIS:")
print("=" * 70)

if found_ports:
    print("✅ Proxy port(s) detected - Split Tunneling may be working!")
    print(f"   Try manually testing port: {found_ports[0]}")
elif vpn_found:
    print("⚠️  VPN is connected but no proxy detected")
    print("   • Split Tunneling may not be enabled")
    print("   • Or ProtonVPN version doesn't support it")
    print("   • Try restarting ProtonVPN completely")
else:
    print("❌ ProtonVPN is NOT connected to a server")
    print("   1. Open ProtonVPN")
    print("   2. Click 'Quick Connect' or select a server")
    print("   3. Wait for 'Connected' status (green)")
    print("   4. THEN enable Split Tunneling in Settings")
    print("   5. Add Python to Included Apps")
    print("   6. Restart ProtonVPN and reconnect")

print("=" * 70)
