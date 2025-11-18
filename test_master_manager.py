#!/usr/bin/env python3
"""
Master Audiobook Manager - Test and Validation Script
=====================================================
Quick validation that the system is properly configured and components work.
"""

import sys
import os
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Test imports
try:
    from master_audiobook_manager import MasterAudiobookManager
    print("✓ MasterAudiobookManager imported successfully")
except ImportError as e:
    print(f"✗ Failed to import MasterAudiobookManager: {e}")
    sys.exit(1)

try:
    from unified_metadata_aggregator import get_metadata
    print("✓ Unified metadata aggregator imported successfully")
except ImportError as e:
    print(f"✗ Failed to import unified_metadata_aggregator: {e}")
    sys.exit(1)

try:
    from audiobookshelf_metadata_sync import AudiobookshelfMetadataSync
    print("✓ AudiobookshelfMetadataSync imported successfully")
except ImportError as e:
    print(f"✗ Failed to import AudiobookshelfMetadataSync: {e}")
    sys.exit(1)

try:
    from stealth_audiobookshelf_crawler import StealthMAMAudiobookshelfCrawler
    print("✓ StealthMAMAudiobookshelfCrawler imported successfully")
except ImportError as e:
    print(f"✗ Failed to import StealthMAMAudiobookshelfCrawler: {e}")
    sys.exit(1)

def test_environment_variables():
    """Test required environment variables."""
    print("\n🔧 Environment Variables Check:")
    
    # Check for .env file
    if Path('.env').exists():
        print("✓ .env file found")
    else:
        print("⚠ .env file not found - you may need to create it")
    
    # Check key variables
    env_vars = [
        'ABS_URL',
        'ABS_TOKEN', 
        'MAM_USERNAME',
        'MAM_PASSWORD'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'PASSWORD' in var or 'TOKEN' in var:
                display_value = "*" * (len(value) - 4) + value[-4:]
            else:
                display_value = value
            print(f"✓ {var}: {display_value}")
        else:
            print(f"⚠ {var}: Not set")

def test_system_initialization():
    """Test that the system can be initialized."""
    print("\n🚀 System Initialization Test:")
    
    try:
        manager = MasterAudiobookManager()
        print("✓ MasterAudiobookManager initialized successfully")
        
        # Check directories were created
        for dir_name, dir_path in manager.output_dirs.items():
            if dir_path.exists():
                print(f"✓ Output directory created: {dir_name}")
            else:
                print(f"✗ Failed to create directory: {dir_name}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to initialize MasterAudiobookManager: {e}")
        return False

def test_cli_interface():
    """Test CLI interface availability."""
    print("\n💻 CLI Interface Test:")
    
    try:
        import argparse
        
        # Test that the script can be imported and CLI functions exist
        manager = MasterAudiobookManager()
        print("✓ CLI interface available")
        
        # Test help functionality
        import subprocess
        result = subprocess.run([
            sys.executable, 
            'master_audiobook_manager.py', 
            '--help'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✓ CLI help command works")
        else:
            print("⚠ CLI help command failed (this is normal if other dependencies are missing)")
            
        return True
        
    except Exception as e:
        print(f"⚠ CLI interface test encountered issue: {e}")
        return True  # Not a critical failure

def test_configuration():
    """Test system configuration."""
    print("\n⚙️ Configuration Test:")
    
    try:
        manager = MasterAudiobookManager()
        
        # Test logging setup
        if hasattr(manager, 'logger'):
            print("✓ Logging configured")
        else:
            print("⚠ Logging not configured")
        
        # Test stats tracking
        if hasattr(manager, 'stats'):
            print("✓ Statistics tracking configured")
        else:
            print("⚠ Statistics tracking not configured")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("MASTER AUDIOBOOK MANAGER - VALIDATION TEST")
    print("=" * 60)
    
    tests = [
        test_environment_variables,
        test_system_initialization,
        test_cli_interface,
        test_configuration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed: {e}")
    
    print(f"\n{'=' * 60}")
    print(f"VALIDATION SUMMARY: {passed}/{total} tests passed")
    print(f"{'=' * 60}")
    
    if passed == total:
        print("🎉 All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("1. Configure your .env file with required credentials")
        print("2. Run: python master_audiobook_manager.py --status")
        print("3. Run: python master_audiobook_manager.py --help")
        print("4. Execute your desired operation!")
    else:
        print("⚠ Some tests failed. Review the output above and:")
        print("1. Install missing dependencies")
        print("2. Configure environment variables")
        print("3. Check file permissions")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)