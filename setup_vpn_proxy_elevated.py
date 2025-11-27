#!/usr/bin/env python3
"""
VPN Port Proxy Setup - Works in Both CMD and PowerShell
This script configures Windows port proxy to route qBittorrent through VPN
"""

import subprocess
import sys
import os
from pathlib import Path


def check_admin_alternative():
    """Check admin privileges using netsh command (works in both CMD and PowerShell)."""
    try:
        # Try to run a netsh command that requires admin - if it succeeds, we have admin
        result = subprocess.run(
            'netsh interface portproxy show all',
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        # If we get here without permission denied, we likely have admin
        return 'Access is denied' not in result.stderr
    except:
        return False


def is_admin():
    """Check if running with administrator privileges (multiple methods)."""
    # Method 1: Try ctypes (works in CMD)
    try:
        import ctypes
        return ctypes.windll.shell.IsUserAnAdmin()
    except:
        pass

    # Method 2: Try netsh command (works in PowerShell and CMD)
    return check_admin_alternative()


def run_netsh_command(command: str) -> tuple:
    """Run netsh command and return (success, output)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def setup_vpn_proxy():
    """Setup VPN port proxy for qBittorrent."""

    print("=" * 80)
    print("VPN Port Proxy Setup for qBittorrent")
    print("=" * 80)
    print()

    # Check admin privileges
    if not is_admin():
        print("ERROR: This script requires Administrator privileges!")
        print()
        print("Current shell:", "PowerShell" if "pwsh" in sys.executable.lower() or "powershell" in os.environ.get('PSModulePath', '').lower() else "Command Prompt")
        print()
        print("SOLUTION FOR POWERSHELL:")
        print("  Run this command in PowerShell (with admin):")
        print("  python -c \"import ctypes; ctypes.windll.shell.ShellExecuteEx(lpVerb='runas', lpFile='python.exe', lpParameters='setup_vpn_proxy_elevated.py')\"")
        print()
        print("OR:")
        print("  1. Right-click on Windows PowerShell")
        print("  2. Select 'Run as Administrator'")
        print("  3. cd to: C:\\Users\\dogma\\Projects\\MAMcrawler")
        print("  4. Run: python setup_vpn_proxy_elevated.py")
        print()
        print("ALTERNATIVE - Use Command Prompt (CMD) instead:")
        print("  1. Press Windows Key + R")
        print("  2. Type: cmd")
        print("  3. Press Ctrl+Shift+Enter (runs as admin)")
        print("  4. cd C:\\Users\\dogma\\Projects\\MAMcrawler")
        print("  5. python setup_vpn_proxy_elevated.py")
        return False

    print("[✓] Running with Administrator privileges")
    print()

    # Step 1: Clean up existing proxies
    print("[1] Cleaning up existing proxy configurations...")
    check_cmd = 'netsh interface portproxy show all'
    success, output = run_netsh_command(check_cmd)

    if success and '1080' in output:
        print("    Found existing proxy on port 1080, removing...")
        delete_cmd = 'netsh interface portproxy delete v4tov4 listenport=1080 listenaddress=127.0.0.1'
        success, output = run_netsh_command(delete_cmd)
        if success:
            print("    ✓ Removed existing proxy")
        else:
            print("    ✗ Failed to remove existing proxy")
            return False
    else:
        print("    ✓ No existing proxy found")

    print()

    # Step 2: Create new port proxy
    print("[2] Creating new port proxy configuration...")
    print("    Source:      127.0.0.1:1080")
    print("    Destination: 10.2.0.1:8080 (ProtonVPN interface)")

    add_cmd = 'netsh interface portproxy add v4tov4 listenport=1080 listenaddress=127.0.0.1 connectport=8080 connectaddress=10.2.0.1'
    success, output = run_netsh_command(add_cmd)

    if success:
        print("    ✓ Port proxy created successfully")
    else:
        print("    ✗ Failed to create port proxy")
        print(f"    Error: {output}")
        return False

    print()

    # Step 3: Verify proxy
    print("[3] Verifying port proxy configuration...")
    success, output = run_netsh_command(check_cmd)

    if success and '1080' in output:
        print("    ✓ Proxy verified successfully")
        print()
        print("    Current configuration:")
        for line in output.split('\n'):
            if '1080' in line or 'Listen' in line or 'Connect' in line or '127.0.0.1' in line or '10.2.0.1' in line:
                line_stripped = line.strip()
                if line_stripped:
                    print(f"    {line_stripped}")
    else:
        print("    ✗ Failed to verify proxy")
        return False

    print()
    print("=" * 80)
    print("Configuration Complete!")
    print("=" * 80)
    print()
    print("Next Steps:")
    print("-" * 80)
    print()
    print("1. Configure qBittorrent:")
    print("   • Open qBittorrent")
    print("   • Go to: Tools > Options > Network")
    print("   • Under 'Proxy Server':")
    print("     - Type: SOCKS5")
    print("     - IP Address: 127.0.0.1")
    print("     - Port: 1080")
    print("   • Check: 'Use proxy for peer connections'")
    print("   • Click OK")
    print()
    print("2. Test connectivity:")
    print("   • Run: python check_vpn_connection.py")
    print()
    print("3. Verify port is listening:")
    print("   • Run: netsh interface portproxy show all")
    print()
    print("=" * 80)
    print()

    return True


if __name__ == '__main__':
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    success = setup_vpn_proxy()

    if success:
        print("✓ Setup completed successfully!")
        sys.exit(0)
    else:
        print("✗ Setup failed!")
        sys.exit(1)
