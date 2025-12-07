import socket
import os

def check_port(host, port):
    try:
        print(f"Checking {host}:{port}...", end=" ")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex((host, port))
            if result == 0:
                print("OPEN")
                return True
            else:
                print(f"CLOSED (Error: {result})")
                return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

port = 52095
print("--- Network Diagnostics ---")
check_port('localhost', port)
check_port('127.0.0.1', port)
check_port('192.168.0.48', port)
