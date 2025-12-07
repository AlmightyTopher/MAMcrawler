#!/usr/bin/env python3
"""
MAMcrawler Test System - Single Entry Point
===========================================

Unified testing system entry point that provides easy access to all testing functionality.

This script serves as the main interface for running tests and should be used instead
of individual test scripts or frameworks.

Features:
- Simple command-line interface
- Automatic test discovery
- Multiple output formats
- CI/CD integration
- Test type filtering
- Parallel execution
- Comprehensive reporting

Usage Examples:
    python test_system.py                    # Run all tests
    python test_system.py unit               # Run only unit tests
    python test_system.py unit integration   # Run unit and integration tests
    python test_system.py --parallel         # Run tests in parallel
    python test_system.py --coverage         # Generate coverage reports
    python test_system.py --ci               # CI mode with detailed reporting
    python test_system.py --help             # Show help

Author: Agent 7 - Unified Testing Framework Specialist
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Main entry point that delegates to the appropriate test runner."""

    # Check if virtual environment is being used
    if not (Path(project_root / "venv").exists() or Path(project_root / ".venv").exists()):
        print("WARNING: No virtual environment detected!")
        print("It is recommended to use a virtual environment for testing.")
        print("Run: python -m venv venv && venv\\Scripts\\activate && pip install -r requirements.txt")
        print()

    # Import and run the test runner
    try:
        from test_runner import main as runner_main
        runner_main()
    except ImportError as e:
        print(f"ERROR: Failed to import test runner: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()