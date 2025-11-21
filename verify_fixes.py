"""
Quick Verification Script for Critical Bug Fixes
"""

import os
import sys

print("="*80)
print("MAMcrawler - Critical Bug Fixes Verification")
print("="*80)

# Test 1: Check DEBUG environment variable usage in mam_crawler.py
print("\n1. Testing Security Fix (Login Response Logging)...")
try:
    with open('mam_crawler.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "debug_mode = os.getenv('DEBUG'" in content and 'if debug_mode:' in content:
        print("   ✅ PASS: Login response logging is conditional on DEBUG mode")
    else:
        print("   ❌ FAIL: DEBUG mode check not found")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# Test 2: Check UnboundLocalError fix
print("\n2. Testing UnboundLocalError Fix...")
try:
    with open('mam_crawler.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the section
    found_proper_scoping = False
    for i in range(len(lines) - 5):
        if "if data.get('content'):" in lines[i]:
            # Check if summary generation is within the next 15 lines with proper indentation
            for j in range(i+1, min(i+15, len(lines))):
                if "if len(content) > 1000:" in lines[j]:
                    # Check indentation
                    base_indent = len(lines[i]) - len(lines[i].lstrip())
                    summary_indent = len(lines[j]) - len(lines[j].lstrip())
                    if summary_indent > base_indent:
                        found_proper_scoping = True
                        break
            if found_proper_scoping:
                break
    
    if found_proper_scoping:
        print("   ✅ PASS: Summary generation is properly scoped inside content block")
    else:
        print("   ❌ FAIL: Variable scoping issue may still exist")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# Test 3: Check requirements.txt
print("\n3. Testing Requirements.txt Completeness...")
try:
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        requirements = f.read().lower()
    
    critical_packages = [
        'qbittorrent-api',
        'crawl4ai',
        'numpy',
        'fastapi',
        'sentence-transformers',
        'faiss-cpu',
        'anthropic',
        'watchdog'
    ]
    
    missing = [pkg for pkg in critical_packages if pkg.lower() not in requirements]
    
    if not missing:
        print(f"   ✅ PASS: All {len(critical_packages)} critical packages found")
    else:
        print(f"   ❌ FAIL: Missing packages: {', '.join(missing)}")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# Test 4: Check database.py
print("\n4. Testing Database Query Execution...")
try:
    with open('database.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'cursor.execute(query, chunk_ids)' in content:
        print("   ✅ PASS: Database query execution is correct")
    else:
        print("   ❌ FAIL: cursor.execute() call may be missing")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# Test 5: Check CORS configuration
print("\n5. Testing CORS Configuration...")
try:
    with open('backend/config.py', 'r', encoding='utf-8') as f:
        config_content = f.read()
    
    if 'ALLOWED_ORIGINS' in config_content and 'ALLOWED_HOSTS' in config_content:
        print("   ✅ PASS: CORS configuration variables exist")
    else:
        print("   ❌ FAIL: CORS configuration may be incomplete")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# Test 6: Check middleware
print("\n6. Testing Security Middleware...")
try:
    with open('backend/middleware.py', 'r', encoding='utf-8') as f:
        middleware_content = f.read()
    
    if 'ALLOWED_ORIGINS' in middleware_content and 'CORSMiddleware' in middleware_content:
        print("   ✅ PASS: CORS middleware uses environment configuration")
    else:
        print("   ❌ FAIL: CORS middleware may not use environment variables")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

print("\n" + "="*80)
print("Verification Complete!")
print("="*80)
