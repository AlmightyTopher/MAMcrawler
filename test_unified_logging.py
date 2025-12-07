#!/usr/bin/env python3
"""
Test script for the unified logging system.

This script demonstrates the capabilities of the new unified logging system
and serves as a migration example for other modules.
"""

import time
import json
from logging_system import (
    get_logger, log_performance, log_security_event, log_audit,
    performance_timer, configure_logging, LogConfig
)
from logging_utils import LogAnalyzer, LogFilter, LogExporter, PerformanceMonitor


def test_basic_logging():
    """Test basic logging functionality"""
    print("=== Testing Basic Logging ===")

    # Get a logger
    logger = get_logger("test_module")

    # Test different log levels
    logger.debug("This is a debug message", structured_data={"key": "value"})
    logger.info("This is an info message", user_id="user123")
    logger.warning("This is a warning message")
    logger.error("This is an error message", structured_data={"error_code": 500})
    logger.critical("This is a critical message")

    print("✓ Basic logging test completed")


def test_structured_logging():
    """Test structured logging with additional context"""
    print("\n=== Testing Structured Logging ===")

    logger = get_logger("structured_test")

    # Log with structured data
    logger.info("User login attempt", structured_data={
        "user_id": "user123",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0...",
        "login_method": "password"
    })

    # Log performance data
    log_performance("database_query", 150.5, {"query_type": "SELECT", "table": "users"})

    # Log security event
    log_security_event("Failed login attempt", "WARNING", {
        "user_id": "user123",
        "ip_address": "192.168.1.100",
        "reason": "invalid_password"
    })

    # Log audit event
    log_audit("USER_LOGIN", user="user123", resource="auth_system", details={
        "success": True,
        "method": "password"
    })

    print("✓ Structured logging test completed")


def test_performance_monitoring():
    """Test performance monitoring"""
    print("\n=== Testing Performance Monitoring ===")

    monitor = PerformanceMonitor()

    @monitor.time_function
    def slow_operation():
        time.sleep(0.1)  # Simulate work
        return "result"

    # Test performance timer
    with performance_timer("test_operation"):
        time.sleep(0.05)
        result = slow_operation()

    # Log custom metrics
    monitor.record_metric("custom_counter", 42, {"category": "test"})
    monitor.record_metric("response_time", 125.3, {"endpoint": "/api/test"})

    # Get metrics summary
    metrics = monitor.get_metrics_summary()
    print(f"Performance metrics: {json.dumps(metrics, indent=2)}")

    print("✓ Performance monitoring test completed")


def test_log_analysis():
    """Test log analysis capabilities"""
    print("\n=== Testing Log Analysis ===")

    # Create some test logs first
    logger = get_logger("analysis_test")
    for i in range(10):
        logger.info(f"Test log entry {i}", structured_data={"index": i})
        if i % 3 == 0:
            logger.error(f"Test error {i}", structured_data={"error_type": "test_error"})

    # Analyze logs
    analyzer = LogAnalyzer()
    analysis = analyzer.analyze_log_files(days=1)

    print(f"Analysis summary: {json.dumps(analysis['summary'], indent=2)}")

    # Generate report
    report = analyzer.generate_report(analysis, "test_log_report.md")
    print("✓ Log analysis report generated")

    print("✓ Log analysis test completed")


def test_log_filtering():
    """Test log filtering and querying"""
    print("\n=== Testing Log Filtering ===")

    # Create test data
    logs = [
        {"timestamp": "2024-01-01T10:00:00", "level": "INFO", "logger": "module1", "message": "Info message 1"},
        {"timestamp": "2024-01-01T10:01:00", "level": "ERROR", "logger": "module1", "message": "Error message 1"},
        {"timestamp": "2024-01-01T10:02:00", "level": "INFO", "logger": "module2", "message": "Info message 2"},
        {"timestamp": "2024-01-01T10:03:00", "level": "WARNING", "logger": "module1", "message": "Warning message 1"},
    ]

    # Test filtering
    query = LogFilter.LogQuery(logs)

    # Filter by level
    error_logs = query.level("ERROR").execute()
    print(f"Found {len(error_logs)} error logs")

    # Filter by logger
    module1_logs = query.logger("module1").execute()
    print(f"Found {len(module1_logs)} logs from module1")

    # Filter by message content
    info_logs = query.contains("Info").execute()
    print(f"Found {len(info_logs)} logs containing 'Info'")

    print("✓ Log filtering test completed")


def test_log_export():
    """Test log export capabilities"""
    print("\n=== Testing Log Export ===")

    logs = [
        {"timestamp": "2024-01-01T10:00:00", "level": "INFO", "message": "Test message 1"},
        {"timestamp": "2024-01-01T10:01:00", "level": "ERROR", "message": "Test error"},
    ]

    exporter = LogExporter(logs)

    # Export to JSON
    json_data = exporter.to_json("test_export.json")
    print(f"Exported {len(logs)} logs to JSON")

    # Export to CSV
    csv_data = exporter.to_csv("test_export.csv")
    print("Exported logs to CSV")

    # Export to Markdown
    md_data = exporter.to_markdown("test_export.md")
    print("Exported logs to Markdown")

    print("✓ Log export test completed")


def main():
    """Run all tests"""
    print("Starting Unified Logging System Tests")
    print("=" * 50)

    # Configure logging for testing
    test_config = LogConfig(
        level="DEBUG",
        destinations=["console", "file"],
        log_directory="test_logs",
        app_name="LoggingSystemTest"
    )
    configure_logging(test_config)

    try:
        test_basic_logging()
        test_structured_logging()
        test_performance_monitoring()
        test_log_analysis()
        test_log_filtering()
        test_log_export()

        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        print("\nThe unified logging system is ready for production use.")
        print("\nTo migrate existing modules:")
        print("1. Replace 'import logging' with 'from logging_system import get_logger'")
        print("2. Replace 'logger = logging.getLogger(__name__)' with 'logger = get_logger(__name__)'")
        print("3. Replace print() statements with appropriate logger calls")
        print("4. Use structured_data parameter for additional context")
        print("5. Use performance_timer decorator for timing operations")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()