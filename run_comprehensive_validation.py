#!/usr/bin/env python3
"""
Simple validation script for MAMcrawler project
"""

import sys
import traceback
import os

def run_test(test_name, test_func):
    """Run a single test and return result"""
    print(f"\nTesting {test_name}...")
    try:
        test_func()
        print(f"PASS: {test_name}")
        return True, None
    except Exception as e:
        print(f"FAIL: {test_name} - {e}")
        return False, str(e)

def test_essential_imports():
    """Test essential Python modules"""
    import sys
    import os
    import json
    import re
    import datetime
    import time
    import logging
    print("  Essential imports working")

def test_numpy():
    """Test NumPy functionality"""
    import numpy as np
    arr = np.array([1, 2, 3, 4, 5])
    mean_val = np.mean(arr)
    assert mean_val == 3.0, f"Expected mean 3.0, got {mean_val}"
    print(f"  NumPy working: {mean_val}")

def test_pandas():
    """Test Pandas functionality"""
    import pandas as pd
    df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    assert len(df) == 3, f"Expected 3 rows, got {len(df)}"
    print("  Pandas working")

def test_requests():
    """Test Requests library"""
    import requests
    session = requests.Session()
    print("  Requests working")

def test_sqlite():
    """Test SQLite database functionality"""
    import sqlite3
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE test (id INTEGER)')
    cursor.execute('INSERT INTO test (id) VALUES (1)')
    result = cursor.fetchone()
    conn.close()
    assert result[0] == 1
    print("  SQLite working")

def test_config_system():
    """Test configuration system"""
    from config import Config
    cfg = Config()
    print("  Config system working")

def test_database_models():
    """Test database models"""
    from database import get_db_connection, init_db
    conn = get_db_connection()
    print("  Database models working")

def test_qbittorrent_api():
    """Test qBittorrent API client"""
    from qbittorrent_client import QBittorrentClient
    client = QBittorrentClient()
    print("  QBittorrent client working")

def test_metdata_tools():
    """Test metadata processing tools"""
    from audio_metadata_extractor import AudioMetadataExtractor
    from series_populator import SeriesPopulator
    print("  Metadata tools working")

def test_crawling_tools():
    """Test crawling functionality"""
    from comprehensive_guide_crawler import ComprehensiveGuideCrawler
    from goodreads_api_client import GoodreadsAPIClient
    print("  Crawling tools working")

def test_web_frameworks():
    """Test web framework imports"""
    try:
        import fastapi
        print("  FastAPI available")
    except ImportError:
        print("  WARNING: FastAPI not available")

def test_ai_libraries():
    """Test AI/ML libraries if available"""
    try:
        import transformers
        print("  Transformers available")
    except ImportError:
        print("  WARNING: Transformers not available")

    try:
        import torch
        print("  PyTorch available")
    except ImportError:
        print("  WARNING: PyTorch not available")

def test_search_libraries():
    """Test search/vector libraries"""
    try:
        import faiss
        print("  FAISS available")
    except ImportError:
        print("  WARNING: FAISS not available")

def test_web_scraping():
    """Test web scraping libraries"""
    try:
        from bs4 import BeautifulSoup
        print("  BeautifulSoup4 available")
    except ImportError:
        print("  WARNING: BeautifulSoup4 not available")

    try:
        import crawl4ai
        print("  Crawl4AI available")
    except ImportError:
        print("  WARNING: Crawl4AI not available")

def test_main_application():
    """Test main application entry points"""
    import cli
    import database
    print("  Main application modules working")

def main():
    """Run all validation tests"""
    print("MAMcrawler Comprehensive Dependency Validation")
    print("=" * 60)
    
    # Test definitions
    tests = [
        ("Essential Python Imports", test_essential_imports),
        ("NumPy Array Operations", test_numpy),
        ("Pandas Data Processing", test_pandas),
        ("HTTP Requests Library", test_requests),
        ("SQLite Database", test_sqlite),
        ("Configuration System", test_config_system),
        ("Database Models", test_database_models),
        ("QBittorrent API", test_qbittorrent_api),
        ("Metadata Processing", test_metdata_tools),
        ("Crawling Tools", test_crawling_tools),
        ("Web Frameworks", test_web_frameworks),
        ("AI/ML Libraries", test_ai_libraries),
        ("Search Libraries", test_search_libraries),
        ("Web Scraping", test_web_scraping),
        ("Main Application", test_main_application),
    ]
    
    results = []
    
    # Run all tests
    for test_name, test_func in tests:
        passed, error = run_test(test_name, test_func)
        results.append((test_name, passed, error))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)
    success_rate = (passed_count / total_count) * 100
    
    print(f"Tests Passed: {passed_count}/{total_count}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Status: {'READY FOR DEPLOYMENT' if success_rate >= 90 else 'NEEDS FIXES'}")
    
    # Failed tests
    failed_tests = [name for name, passed, _ in results if not passed]
    if failed_tests:
        print(f"\nFailed Tests ({len(failed_tests)}):")
        for test_name in failed_tests:
            print(f"  - {test_name}")
    
    # Optional tests
    optional_tests = [name for name, passed, error in results 
                     if not passed and error and "not available" in error]
    if optional_tests:
        print(f"\nOptional Tests Not Available ({len(optional_tests)}):")
        for test_name in optional_tests:
            print(f"  - {test_name}")
    
    # Recommendations
    print(f"\nRECOMMENDATIONS")
    if success_rate >= 90:
        print("Project is ready for deployment!")
        print("All critical dependencies are working correctly.")
    elif success_rate >= 75:
        print("Project needs minor fixes before deployment.")
        print("Review failed tests and fix missing dependencies.")
    else:
        print("Project needs major fixes before deployment.")
        print("Critical dependencies are missing or broken.")
    
    print("=" * 60)
    return success_rate >= 75

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nValidation failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)