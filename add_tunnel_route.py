import sys
import os
import subprocess

# Configuration
CONFIG_FILE = r'c:\Users\dogma\Projects\MAMcrawler\mamcrawler_tunnel_config.yml'
TUNNEL_ID = "ce852a83-cc3c-46d7-b5f2-a53e517e4206"
DOMAIN_BASE = "tophertek.com"

def main():
    if len(sys.argv) < 3:
        print("Usage: python add_tunnel_route.py <subdomain> <local_url>")
        print("Example: python add_tunnel_route.py bob http://localhost:3000")
        sys.exit(1)

    subdomain = sys.argv[1]
    local_url = sys.argv[2]
    hostname = f"{subdomain}.{DOMAIN_BASE}"

    # Verify input format for url
    if not local_url.startswith("http"):
        # Assume http if not provided
        if local_url.isdigit():
             local_url = f"http://localhost:{local_url}"
        elif ":" in local_url and not local_url.startswith("http"):
             local_url = f"http://{local_url}"
        else:
             print(f"Warning: URL '{local_url}' does not start with http/https. Assuming valid service string.")

    print(f"Configuring: {hostname} -> {local_url}")

    # 1. Update Config File
    try:
        with open(CONFIG_FILE, 'r') as f:
            lines = f.readlines()

        # Check if already exists
        exists = False
        for line in lines:
            if f"hostname: {hostname}" in line:
                exists = True
                break
        
        if exists:
            print(f"Entry for {hostname} already present in {CONFIG_FILE}. Skipping file edit.")
        else:
            # Find insertion point (before the catch-all)
            insert_idx = -1
            for i, line in enumerate(lines):
                if '- service: http_status:404' in line:
                    insert_idx = i
                    break
            
            if insert_idx != -1:
                new_entry = [
                    f"  - hostname: {hostname}\n",
                    f"    service: {local_url}\n"
                ]
                lines[insert_idx:insert_idx] = new_entry
                
                with open(CONFIG_FILE, 'w') as f:
                    f.writelines(lines)
                print(f"Successfully updated configuration file: {CONFIG_FILE}")
            else:
                print("Error: Could not find catch-all rule ('- service: http_status:404') in config file. Cannot safely insert.")
                sys.exit(1)

    except Exception as e:
        print(f"Error modifying config file: {e}")
        sys.exit(1)

    # 2. Register DNS
    print(f"Registering DNS for {hostname}...")
    cmd = ["cloudflared", "tunnel", "route", "dns", "-f", TUNNEL_ID, hostname]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("DNS route successfully registered with Cloudflare.")
        else:
            print("Failed to register DNS route.")
            print("Error Output:", result.stderr)
            # Proceeding anyway as config was updated, but user should know DNS failed
    except FileNotFoundError:
        print("Error: 'cloudflared' command not found in PATH.")
        sys.exit(1)

    # 3. Restart Service
    print("Restarting cloudflared service to apply changes...")
    # restart-service requires admin. We try, and warn if it fails.
    try:
        cmd_restart = ["powershell", "-Command", "Restart-Service cloudflared"]
        result = subprocess.run(cmd_restart, capture_output=True, text=True)
        if result.returncode == 0:
             print("Service restarted successfully!")
        else:
             print("WARNING: Failed to restart service. Permission denied?")
             print("Run this tool as Administrator, or manually run: Restart-Service cloudflared")
    except Exception as e:
        print(f"Error executing restart command: {e}")

    print("\n" + "="*50)
    print(f"SUCCESS! Configuration updated for https://{hostname}")
    print("="*50)

if __name__ == "__main__":
    main()
