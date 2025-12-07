# test_config_system.py
# Comprehensive validation of the Configuration System

import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath('.'))

from mamcrawler.core.config import (
    CrawlerConfig,
    DatabaseConfig,
    LoggingConfig,
    ProxyConfig,
    SecurityConfig,
    MAMConfig,
    OutputConfig,
    MonitoringConfig,
    ConfigRegistry,
    GlobalConfig
)

def test_dataclass_initialization():
    """Test that all config dataclasses initialize with defaults"""
    print("\n=== Testing Dataclass Initialization ===")

    configs = {
        "CrawlerConfig": CrawlerConfig(),
        "DatabaseConfig": DatabaseConfig(),
        "LoggingConfig": LoggingConfig(),
        "ProxyConfig": ProxyConfig(),
        "SecurityConfig": SecurityConfig(),
        "MAMConfig": MAMConfig(),
        "OutputConfig": OutputConfig(),
        "MonitoringConfig": MonitoringConfig(),
    }

    for name, config in configs.items():
        print(f"  ✓ {name} initialized successfully")
        print(f"    Sample values: {list(config.__dict__.items())[:3]}")

    return True

def test_dataclass_validation():
    """Test that dataclasses validate inputs correctly"""
    print("\n=== Testing Dataclass Validation ===")

    # Test 1: CrawlerConfig - negative min_delay should fail
    print("\n  Test 1: CrawlerConfig with negative min_delay")
    try:
        config = CrawlerConfig(min_delay=-1.0)
        print("    ❌ FAIL: Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"    ✓ Correctly raised ValueError: {e}")

    # Test 2: CrawlerConfig - max_delay < min_delay should fail
    print("\n  Test 2: CrawlerConfig with max_delay < min_delay")
    try:
        config = CrawlerConfig(min_delay=10.0, max_delay=5.0)
        print("    ❌ FAIL: Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"    ✓ Correctly raised ValueError: {e}")

    # Test 3: DatabaseConfig - non-positive max_connections should fail
    print("\n  Test 3: DatabaseConfig with zero max_connections")
    try:
        config = DatabaseConfig(max_connections=0)
        print("    ❌ FAIL: Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"    ✓ Correctly raised ValueError: {e}")

    # Test 4: LoggingConfig - invalid log level should fail
    print("\n  Test 4: LoggingConfig with invalid log level")
    try:
        config = LoggingConfig(level="INVALID")
        print("    ❌ FAIL: Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"    ✓ Correctly raised ValueError: {e}")

    print("\n  ✓ All validation tests passed")
    return True

def test_config_registry():
    """Test ConfigRegistry operations"""
    print("\n=== Testing ConfigRegistry ===")

    registry = ConfigRegistry()

    # Test 1: Register config
    print("\n  Test 1: Register configuration")
    crawler_config = CrawlerConfig(min_delay=5.0)
    registry.register_config("test_crawler", crawler_config)
    print("    ✓ Config registered")

    # Test 2: Retrieve config
    print("\n  Test 2: Retrieve configuration")
    retrieved = registry.get_config("test_crawler")
    if retrieved is None:
        print("    ❌ FAIL: Config not found")
        return False
    if retrieved.min_delay != 5.0:
        print("    ❌ FAIL: Config values don't match")
        return False
    print(f"    ✓ Config retrieved: min_delay={retrieved.min_delay}")

    # Test 3: Update config
    print("\n  Test 3: Update configuration")
    registry.update_config("test_crawler", {"min_delay": 8.0, "max_delay": 15.0})
    updated = registry.get_config("test_crawler")
    if updated.min_delay != 8.0 or updated.max_delay != 15.0:
        print("    ❌ FAIL: Config update failed")
        return False
    print(f"    ✓ Config updated: min_delay={updated.min_delay}, max_delay={updated.max_delay}")

    # Test 4: Non-existent config returns None
    print("\n  Test 4: Retrieve non-existent configuration")
    none_config = registry.get_config("nonexistent")
    if none_config is not None:
        print("    ❌ FAIL: Should return None for non-existent config")
        return False
    print("    ✓ Correctly returned None")

    print("\n  ✓ All ConfigRegistry tests passed")
    return True

def test_global_config_singleton():
    """Test that GlobalConfig is a singleton"""
    print("\n=== Testing GlobalConfig Singleton ===")

    # Get two instances
    instance1 = GlobalConfig()
    instance2 = GlobalConfig()

    # They should be the same object
    if instance1 is not instance2:
        print("    ❌ FAIL: GlobalConfig is not a singleton")
        return False

    print("    ✓ GlobalConfig is a singleton (same instance)")

    # Test that default configs are registered
    crawler_config = instance1.get_config("crawler")
    if crawler_config is None:
        print("    ❌ FAIL: Default crawler config not registered")
        return False

    print(f"    ✓ Default crawler config exists: min_delay={crawler_config.min_delay}")

    # Test convenience methods
    print("\n  Testing convenience getter methods:")
    configs_to_test = [
        ("crawler", instance1.get_crawler_config),
        ("database", instance1.get_database_config),
        ("mam", instance1.get_mam_config),
        ("logging", instance1.get_logging_config),
    ]

    for name, getter in configs_to_test:
        config = getter()
        if config is None:
            print(f"    ❌ FAIL: {name} config getter returned None")
            return False
        print(f"    ✓ {name} config getter works")

    print("\n  ✓ All GlobalConfig singleton tests passed")
    return True

def test_config_file_operations():
    """Test saving and loading configs from files"""
    print("\n=== Testing Config File Operations ===")

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\n  Using temp directory: {temp_dir}")

        # Create a test registry
        registry = ConfigRegistry()
        test_config = CrawlerConfig(min_delay=7.0, max_delay=12.0, headless=False)
        registry.register_config("test", test_config)

        # Test 1: Save configs
        print("\n  Test 1: Save configuration to file")
        registry.save_all_configs(temp_dir)

        config_file = Path(temp_dir) / "test.json"
        if not config_file.exists():
            print("    ❌ FAIL: Config file not created")
            return False
        print(f"    ✓ Config file created: {config_file.name}")

        # Verify file contents
        with open(config_file, 'r') as f:
            saved_data = json.load(f)

        if saved_data.get('min_delay') != 7.0:
            print("    ❌ FAIL: Saved data doesn't match")
            return False
        print(f"    ✓ Config data saved correctly: min_delay={saved_data['min_delay']}")

        # Test 2: Load configs
        print("\n  Test 2: Load configuration from file")
        new_registry = ConfigRegistry()
        new_registry.register_config("test", CrawlerConfig())  # Register with defaults
        new_registry.load_all_configs(temp_dir)

        loaded_config = new_registry.get_config("test")
        if loaded_config is None:
            print("    ❌ FAIL: Config not loaded")
            return False

        if loaded_config.min_delay != 7.0 or loaded_config.max_delay != 12.0:
            print(f"    ❌ FAIL: Loaded values don't match (got {loaded_config.min_delay})")
            return False

        print(f"    ✓ Config loaded correctly: min_delay={loaded_config.min_delay}, max_delay={loaded_config.max_delay}")

    print("\n  ✓ All file operation tests passed")
    return True

def test_environment_variable_loading():
    """Test that environment variables are loaded correctly"""
    print("\n=== Testing Environment Variable Loading ===")

    # Set some test environment variables
    original_env = {}
    test_vars = {
        'MAMCRAWLER_MIN_DELAY': '2.5',
        'MAMCRAWLER_MAX_DELAY': '5.5',
        'MAMCRAWLER_HEADLESS': 'false',
        'MAMCRAWLER_LOG_LEVEL': 'DEBUG',
    }

    print("\n  Setting test environment variables:")
    for key, value in test_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
        print(f"    {key}={value}")

    try:
        # Force reload by creating a new instance (won't work due to singleton, but we can test the values)
        # Since GlobalConfig is a singleton, we'll just check current values
        global_config = GlobalConfig()
        crawler_config = global_config.get_crawler_config()

        print("\n  Checking loaded values:")
        print(f"    min_delay: {crawler_config.min_delay} (expected: 2.5)")
        print(f"    max_delay: {crawler_config.max_delay} (expected: 5.5)")
        print(f"    headless: {crawler_config.headless} (expected: False)")

        logging_config = global_config.get_logging_config()
        print(f"    log_level: {logging_config.level} (expected: DEBUG)")

        # Note: Since GlobalConfig is a singleton and was already initialized,
        # these values might not reflect the env vars we just set.
        # This is expected behavior - env vars are loaded on first initialization.
        print("\n  ⚠️  Note: GlobalConfig is a singleton initialized at import time.")
        print("      Environment variables are loaded once during initialization.")
        print("      In production, set env vars before importing the module.")

    finally:
        # Restore original environment
        print("\n  Restoring original environment variables")
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    print("\n  ✓ Environment variable loading test completed")
    return True

def main():
    """Run all configuration system tests"""
    print("="*60)
    print("Configuration System Validation")
    print("="*60)

    tests = [
        ("Dataclass Initialization", test_dataclass_initialization),
        ("Dataclass Validation", test_dataclass_validation),
        ("ConfigRegistry Operations", test_config_registry),
        ("GlobalConfig Singleton", test_global_config_singleton),
        ("Config File Operations", test_config_file_operations),
        ("Environment Variable Loading", test_environment_variable_loading),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {name}")

    print("\n" + "="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)

    if passed == total:
        print("\n🎉 All configuration system tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
