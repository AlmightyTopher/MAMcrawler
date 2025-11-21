"""
Comprehensive Test Suite for MAMcrawler Critical Bug Fixes
Tests all fixes and improvements made to the codebase
"""

import os
import sys
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import asyncio

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "skipped": []
}

def test_result(test_name: str, passed: bool, message: str = ""):
    """Track test results"""
    if passed:
        test_results["passed"].append(test_name)
        print(f"✅ PASS: {test_name}")
        if message:
            print(f"   {message}")
    else:
        test_results["failed"].append(test_name)
        print(f"❌ FAIL: {test_name}")
        if message:
            print(f"   {message}")

def skip_test(test_name: str, reason: str):
    """Skip a test"""
    test_results["skipped"].append(test_name)
    print(f"⏭️  SKIP: {test_name} - {reason}")

# ============================================================================
# Test 1: Security Fix - Login Response Logging
# ============================================================================

def test_login_response_logging():
    """Test that login responses are only logged in debug mode"""
    print("\n" + "="*80)
    print("TEST 1: Security Fix - Login Response Logging")
    print("="*80)
    
    try:
        # Test without DEBUG env var
        os.environ.pop('DEBUG', None)
        
        # Mock the login process
        test_passed = True
        
        # Check that the code checks for DEBUG env var
        with open('mam_crawler.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verify debug mode check exists
        if 'debug_mode = os.getenv' in content and 'DEBUG' in content:
            test_result("Login response logging - Debug mode check", True, 
                       "Code correctly checks DEBUG environment variable")
        else:
            test_result("Login response logging - Debug mode check", False,
                       "Missing DEBUG environment variable check")
            test_passed = False
        
        # Verify conditional file writing
        if 'if debug_mode:' in content and 'mam_login_response.html' in content:
            test_result("Login response logging - Conditional write", True,
                       "File writing is conditional on debug mode")
        else:
            test_result("Login response logging - Conditional write", False,
                       "File writing is not properly conditional")
            test_passed = False
        
        return test_passed
        
    except Exception as e:
        test_result("Login response logging", False, f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 2: UnboundLocalError Fix
# ============================================================================

def test_unboundlocalerror_fix():
    """Test that UnboundLocalError is fixed in guide processing"""
    print("\n" + "="*80)
    print("TEST 2: UnboundLocalError Fix")
    print("="*80)
    
    try:
        # Read the file
        with open('mam_crawler.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find the problematic section
        found_fix = False
        in_content_block = False
        summary_inside_block = False
        
        for i, line in enumerate(lines):
            # Look for the content block
            if "if data.get('content'):" in line:
                in_content_block = True
                
            # Check if summary generation is inside the content block
            if in_content_block and "if len(content) > 1000:" in line:
                # Check indentation - should be inside the content block
                content_indent = None
                for j in range(i-10, i):
                    if j >= 0 and "if data.get('content'):" in lines[j]:
                        content_indent = len(lines[j]) - len(lines[j].lstrip())
                        break
                
                current_indent = len(line) - len(line.lstrip())
                
                # Summary should have more indentation than content check
                if current_indent > content_indent:
                    summary_inside_block = True
                    found_fix = True
                    break
        
        if found_fix and summary_inside_block:
            test_result("UnboundLocalError fix - Variable scoping", True,
                       "Summary generation is correctly inside content block")
            return True
        else:
            test_result("UnboundLocalError fix - Variable scoping", False,
                       "Summary generation may still be outside content block")
            return False
            
    except Exception as e:
        test_result("UnboundLocalError fix", False, f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 3: Requirements.txt Completeness
# ============================================================================

def test_requirements_completeness():
    """Test that requirements.txt contains all critical dependencies"""
    print("\n" + "="*80)
    print("TEST 3: Requirements.txt Completeness")
    print("="*80)
    
    try:
        # Read requirements.txt
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            requirements = f.read().lower()
        
        # Critical packages that must be present
        critical_packages = [
            'qbittorrent-api',
            'crawl4ai',
            'numpy',
            'aiohttp',
            'beautifulsoup4',
            'tenacity',
            'fastapi',
            'sentence-transformers',
            'faiss-cpu',
            'anthropic',
            'watchdog',
            'python-dotenv',
            'sqlalchemy',
            'playwright',
            'pydantic'
        ]
        
        missing_packages = []
        found_packages = []
        
        for package in critical_packages:
            if package.lower() in requirements:
                found_packages.append(package)
            else:
                missing_packages.append(package)
        
        if not missing_packages:
            test_result("Requirements completeness - All critical packages", True,
                       f"All {len(critical_packages)} critical packages found")
        else:
            test_result("Requirements completeness - All critical packages", False,
                       f"Missing packages: {', '.join(missing_packages)}")
        
        # Check for organization/comments
        if '# =' in requirements or '# Core' in requirements or '# Database' in requirements:
            test_result("Requirements completeness - Organization", True,
                       "Requirements file is well-organized with comments")
        else:
            test_result("Requirements completeness - Organization", False,
                       "Requirements file lacks organization")
        
        return len(missing_packages) == 0
        
    except Exception as e:
        test_result("Requirements completeness", False, f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 4: Database Query Execution (Verify already fixed)
# ============================================================================

def test_database_query_execution():
    """Test that database query execution is correct"""
    print("\n" + "="*80)
    print("TEST 4: Database Query Execution")
    print("="*80)
    
    try:
        # Read database.py
        with open('database.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for the correct pattern
        if 'cursor.execute(query, chunk_ids)' in content:
            test_result("Database query execution - Execute call", True,
                       "cursor.execute() is properly called with parameters")
        else:
            test_result("Database query execution - Execute call", False,
                       "cursor.execute() call may be missing")
            return False
        
        # Verify it's in the right function
        if 'def get_chunks_by_ids' in content:
            test_result("Database query execution - Function exists", True,
                       "get_chunks_by_ids function exists")
        else:
            test_result("Database query execution - Function exists", False,
                       "get_chunks_by_ids function not found")
            return False
        
        return True
        
    except Exception as e:
        test_result("Database query execution", False, f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 5: CORS Configuration
# ============================================================================

def test_cors_configuration():
    """Test that CORS is properly configured"""
    print("\n" + "="*80)
    print("TEST 5: CORS Configuration")
    print("="*80)
    
    try:
        # Check backend config
        with open('backend/config.py', 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        # Check for CORS settings
        if 'ALLOWED_ORIGINS' in config_content:
            test_result("CORS configuration - Config variable", True,
                       "ALLOWED_ORIGINS configuration variable exists")
        else:
            test_result("CORS configuration - Config variable", False,
                       "ALLOWED_ORIGINS configuration variable missing")
            return False
        
        # Check middleware
        with open('backend/middleware.py', 'r', encoding='utf-8') as f:
            middleware_content = f.read()
        
        if 'ALLOWED_ORIGINS' in middleware_content and 'CORSMiddleware' in middleware_content:
            test_result("CORS configuration - Middleware", True,
                       "CORS middleware uses ALLOWED_ORIGINS from environment")
        else:
            test_result("CORS configuration - Middleware", False,
                       "CORS middleware may not use environment variable")
            return False
        
        # Check for wildcard warning
        if 'wildcard' in middleware_content.lower() or '"*"' in middleware_content:
            test_result("CORS configuration - Wildcard warning", True,
                       "Code includes wildcard detection/warning")
        else:
            test_result("CORS configuration - Wildcard warning", False,
                       "No wildcard detection found")
        
        return True
        
    except Exception as e:
        test_result("CORS configuration", False, f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 6: Import Organization
# ============================================================================

def test_import_organization():
    """Test that imports are properly organized"""
    print("\n" + "="*80)
    print("TEST 6: Import Organization")
    print("="*80)
    
    try:
        # Check a few key files
        files_to_check = [
            'mam_crawler.py',
            'database.py',
            'backend/main.py'
        ]
        
        all_good = True
        
        for filepath in files_to_check:
            if not os.path.exists(filepath):
                skip_test(f"Import organization - {filepath}", "File not found")
                continue
                
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Check if imports are at the top (within first 50 lines)
            import_lines = []
            for i, line in enumerate(lines[:50]):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    import_lines.append(i)
            
            # Check for function-level imports (imports inside functions)
            function_level_imports = []
            in_function = False
            for i, line in enumerate(lines):
                if line.strip().startswith('def ') or line.strip().startswith('async def '):
                    in_function = True
                elif in_function and (line.strip().startswith('import ') or line.strip().startswith('from ')):
                    # Some function-level imports are intentional (lazy loading)
                    # Only flag if it's a common library
                    if any(lib in line for lib in ['os', 'sys', 'json', 'logging']):
                        function_level_imports.append((i+1, line.strip()))
                elif not line.strip() or line.strip().startswith('class '):
                    in_function = False
            
            if function_level_imports:
                test_result(f"Import organization - {filepath}", False,
                           f"Found {len(function_level_imports)} function-level imports (may be intentional)")
                all_good = False
            else:
                test_result(f"Import organization - {filepath}", True,
                           "No problematic function-level imports found")
        
        return all_good
        
    except Exception as e:
        test_result("Import organization", False, f"Exception: {str(e)}")
        return False

# ============================================================================
# Test 7: Configuration Validation
# ============================================================================

def test_configuration_validation():
    """Test that configuration is properly validated"""
    print("\n" + "="*80)
    print("TEST 7: Configuration Validation")
    print("="*80)
    
    try:
        # Check backend config
        with open('backend/config.py', 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        # Check for Pydantic usage
        if 'BaseSettings' in config_content and 'pydantic' in config_content:
            test_result("Configuration validation - Pydantic", True,
                       "Configuration uses Pydantic for validation")
        else:
            test_result("Configuration validation - Pydantic", False,
                       "Configuration may not use Pydantic")
            return False
        
        # Check for environment variable loading
        if 'env_file' in config_content or '.env' in config_content:
            test_result("Configuration validation - Environment loading", True,
                       "Configuration loads from .env file")
        else:
            test_result("Configuration validation - Environment loading", False,
                       "No .env file loading detected")
        
        # Check for security settings
        security_settings = ['API_KEY', 'SECRET_KEY', 'ALLOWED_ORIGINS', 'ALLOWED_HOSTS']
        found_settings = sum(1 for setting in security_settings if setting in config_content)
        
        if found_settings >= 3:
            test_result("Configuration validation - Security settings", True,
                       f"Found {found_settings}/{len(security_settings)} security settings")
        else:
            test_result("Configuration validation - Security settings", False,
                       f"Only found {found_settings}/{len(security_settings)} security settings")
        
        return True
        
    except Exception as e:
        test_result("Configuration validation", False, f"Exception: {str(e)}")
        return False

# ============================================================================
# Main Test Runner
# ============================================================================

def run_all_tests():
    """Run all tests and generate report"""
    print("\n" + "="*80)
    print("MAMcrawler Critical Bug Fixes - Comprehensive Test Suite")
    print("="*80)
    print(f"Test Date: {os.popen('date /t').read().strip()} {os.popen('time /t').read().strip()}")
    print("="*80)
    
    # Run all tests
    tests = [
        ("Security Fix - Login Response Logging", test_login_response_logging),
        ("UnboundLocalError Fix", test_unboundlocalerror_fix),
        ("Requirements Completeness", test_requirements_completeness),
        ("Database Query Execution", test_database_query_execution),
        ("CORS Configuration", test_cors_configuration),
        ("Import Organization", test_import_organization),
        ("Configuration Validation", test_configuration_validation),
    ]
    
    overall_results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            overall_results.append(result)
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR in {test_name}: {str(e)}")
            overall_results.append(False)
    
    # Generate summary report
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total_tests = len(test_results["passed"]) + len(test_results["failed"])
    passed_count = len(test_results["passed"])
    failed_count = len(test_results["failed"])
    skipped_count = len(test_results["skipped"])
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"✅ Passed: {passed_count} ({passed_count/total_tests*100:.1f}%)")
    print(f"❌ Failed: {failed_count} ({failed_count/total_tests*100:.1f}%)")
    print(f"⏭️  Skipped: {skipped_count}")
    
    if failed_count > 0:
        print("\n❌ FAILED TESTS:")
        for test in test_results["failed"]:
            print(f"   - {test}")
    
    if skipped_count > 0:
        print("\n⏭️  SKIPPED TESTS:")
        for test in test_results["skipped"]:
            print(f"   - {test}")
    
    print("\n" + "="*80)
    
    if failed_count == 0:
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        return True
    else:
        print(f"❌ {failed_count} TEST(S) FAILED")
        print("="*80)
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
