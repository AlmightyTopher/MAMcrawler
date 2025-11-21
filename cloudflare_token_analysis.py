#!/usr/bin/env python3
"""
Cloudflare Tunnel Token Analysis Tool
Analyzes JWT token structure and identifies potential connection issues
"""

import base64
import json
import sys
from datetime import datetime

def decode_jwt_segment(segment):
    """Decode a JWT segment with proper padding"""
    # Add padding if needed
    padding = 4 - len(segment) % 4
    if padding != 4:
        segment += '=' * padding
    
    try:
        decoded = base64.urlsafe_b64decode(segment)
        return decoded.decode('utf-8')
    except Exception as e:
        return f"Decode error: {e}"

def analyze_cloudflare_token(token):
    """Analyze the Cloudflare Tunnel token"""
    print("="*60)
    print("CLOUDFLARE TUNNEL TOKEN ANALYSIS")
    print("="*60)
    
    # Split token into parts
    parts = token.split('.')
    
    if len(parts) != 3:
        print(f"[X] TOKEN FORMAT ERROR: Expected 3 parts, got {len(parts)}")
        return False
    
    header_b64, payload_b64, signature_b64 = parts
    
    print(f"\nA) TOKEN FORMAT CHECK:")
    print(f"   Header:   {header_b64[:50]}...")
    print(f"   Payload:  {payload_b64[:50]}...")
    print(f"   Signature: {'Present' if signature_b64 else 'MISSING'}")
    
    # Decode header
    try:
        header_json = decode_jwt_segment(header_b64)
        header = json.loads(header_json)
        print(f"\n   Header Contents:")
        for key, value in header.items():
            print(f"     {key}: {value}")
    except Exception as e:
        print(f"   [X] Header decode error: {e}")
        return False
    
    # Decode payload
    try:
        payload_json = decode_jwt_segment(payload_b64)
        payload = json.loads(payload_json)
        print(f"\n   Payload Contents:")
        for key, value in payload.items():
            print(f"     {key}: {value}")
    except Exception as e:
        print(f"   [X] Payload decode error: {e}")
        return False
    
    # Analyze specific fields
    print(f"\nB) TOKEN VALIDATION:")
    
    # Check required fields
    required_fields = ['kid', 'iss', 'sub']
    missing_fields = []
    
    for field in required_fields:
        if field not in payload:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"   [X] Missing required fields: {', '.join(missing_fields)}")
    else:
        print(f"   [OK] All required fields present")
    
    # Check expiration
    if 'exp' in payload:
        exp_timestamp = payload['exp']
        exp_date = datetime.fromtimestamp(exp_timestamp)
        now = datetime.now()
        
        if exp_date < now:
            print(f"   [X] TOKEN EXPIRED: {exp_date}")
        else:
            days_remaining = (exp_date - now).days
            print(f"   [OK] Token valid for {days_remaining} more days")
    else:
        print(f"   [!] No expiration time found")
    
    # Check tunnel ID pattern
    if 'sub' in payload:
        tunnel_id = payload['sub']
        print(f"   Tunnel ID: {tunnel_id}")
        
        # Cloudflare tunnel IDs are typically UUID-like
        if len(tunnel_id) == 36 and tunnel_id.count('-') == 4:
            print(f"   [OK] Tunnel ID format looks valid (UUID)")
        else:
            print(f"   [!] Tunnel ID format unusual")
    
    return True

if __name__ == "__main__":
    token = "eyJhIjoiOTIzMmE2ZGJlZTQwNjQ3NjhjZmEyNWM1OWUzYTA5ZGYiLCJ0IjoiMjEzMTYwMjktMjE0Yy00ZmJjLWJjMDctNTBmMGRkMTBmZWYzIiwicyI6IlpqVTBNVGd3WXprdE5tVmtaUzAwTXprMUxUaGpZamN0WWpSaVlUaGpNMkV6WmpSayJ9"
    
    analyze_cloudflare_token(token)