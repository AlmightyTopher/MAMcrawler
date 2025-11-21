#!/usr/bin/env python3
"""
Comprehensive Pre-Deployment Validation Script for MAMcrawler System
Validates all core components, dependencies, and system readiness
"""

import sys
import os
import importlib
import traceback
import json
from pathlib import Path

class SystemValidator:
    def __init__(self):
        self.results = {
            'environment': {},
            'dependencies': {},
            'core_modules': {},
            'web_crawler': {},
            'database': {},
            'api_endpoints': {},
            'ai_components': {},
            'file_operations': {},
            'search_capabilities': {},
            'logging': {},
            'configuration': {},
            'tests': {}
        }
        self.errors = []
        self.warnings = []
        
    def log_result(self, category, test, status, message=""):
        """Log validation result"""
        if category not in self.results:
            self.results[category] = {}
        self.results[category][test] = {'status': status, 'message': message}
        status_symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
        print(f"{status_symbol} {category}.{test}: {status} {message}")

    def validate_environment(self):
        """Validate Python environment and virtual environment"""
        print("\n=== ENVIRONMENT VALIDATION ===")
        
        # Python version
        python_version = sys.version_info
        if python_version >= (3, 9):
            self.log_result('environment', 'python_version', 'PASS', f"{python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            self.log_result('environment', 'python_version', 'FAIL', f"Python {python_version.major}.{python_version.minor}.{python_version.micro} - requires 3.9+")
            
        # Virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            venv_path = sys.prefix
            self.log_result('environment', 'virtual_env', 'PASS', f"Active venv: {venv_path}")
        else:
            self.log_result('environment', 'virtual_env', 'WARN', "Not running in virtual environment")
            
        # Working directory
        cwd = os.getcwd()
        if 'MAMcrawler' in cwd:
            self.log_result('environment', 'working_directory', 'PASS', cwd)
        else:
            self.log_result('environment', 'working_directory', 'WARN', f"Unexpected directory: {cwd}")

    def validate_dependencies(self):
        """Validate critical dependencies"""
        print("\n=== DEPENDENCY VALIDATION ===")
        
        critical_deps = [
            'fastapi',
            'uvicorn', 
            'requests',
            'beautifulsoup4',
            'aiohttp',
            'sqlite3',
            'anthropic',
            'langchain',
            'transformers',
            'torch',
            'faiss',
            'playwright',
            'crawl4ai',
            'qbittorrent'
        ]
        
        for dep in critical_deps:
            try:
                if dep == 'sqlite3':
                    import sqlite3
                else:
                    importlib.import_module(dep.replace('-', '_'))
                self.log_result('dependencies', dep, 'PASS')
            except ImportError:
                self.log_result('dependencies', dep, 'FAIL', 'Import failed')

    def validate_core_modules(self):
        """Validate core project modules"""
        print("\n=== CORE MODULES VALIDATION ===")
        
        # Test basic imports
        modules_to_test = [
            'database',
            'config', 
            'mam_crawler_config',
            'cli'
        ]
        
        for module in modules_to_test:
            try:
                sys.path.insert(0, '.')
                importlib.import_module(module)
                self.log_result('core_modules', f'{module}_import', 'PASS')
            except Exception as e:
                self.log_result('core_modules', f'{module}_import', 'FAIL', str(e)[:100])

        # Test specific classes
        try:
            from mam_crawler_config import MAMCrawlingProcedures
            procedures = MAMCrawlingProcedures()
            if hasattr(procedures, 'allowed_endpoints'):
                self.log_result('core_modules', 'MAMCrawlingProcedures_class', 'PASS')
            else:
                self.log_result('core_modules', 'MAMCrawlingProcedures_class', 'FAIL', 'Missing allowed_endpoints')
        except Exception as e:
            self.log_result('core_modules', 'MAMCrawlingProcedures_class', 'FAIL', str(e)[:100])

    def validate_database(self):
        """Validate database functionality"""
        print("\n=== DATABASE VALIDATION ===")
        
        try:
            import sqlite3
            # Test basic SQLite functionality
            conn = sqlite3.connect(':memory:')
            conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')
            conn.execute('INSERT INTO test (id) VALUES (1)')
            cursor = conn.execute('SELECT COUNT(*) FROM test')
            count = cursor.fetchone()[0]
            conn.close()
            
            if count == 1:
                self.log_result('database', 'sqlite_basic', 'PASS')
            else:
                self.log_result('database', 'sqlite_basic', 'FAIL', f'Expected 1, got {count}')
        except Exception as e:
            self.log_result('database', 'sqlite_basic', 'FAIL', str(e)[:100])
            
        # Check if database file exists
        db_files = ['metadata.sqlite', 'database.db', 'audiobooks.db']
        for db_file in db_files:
            if os.path.exists(db_file):
                self.log_result('database', f'{db_file}_exists', 'PASS')
            else:
                self.log_result('database', f'{db_file}_exists', 'WARN', 'File not found')

    def validate_web_crawler(self):
        """Validate web crawling components"""
        print("\n=== WEB CRAWLER VALIDATION ===")
        
        # Test Playwright
        try:
            from playwright.sync_api import sync_playwright
            self.log_result('web_crawler', 'playwright', 'PASS')
        except ImportError:
            self.log_result('web_crawler', 'playwright', 'FAIL', 'Import failed')
            
        # Test Crawl4AI
        try:
            from crawl4ai import AsyncWebCrawler
            self.log_result('web_crawler', 'crawl4ai', 'PASS')
        except ImportError:
            self.log_result('web_crawler', 'crawl4ai', 'FAIL', 'Import failed')
            
        # Test BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup('<html><body>test</body></html>', 'html.parser')
            if soup.body.text == 'test':
                self.log_result('web_crawler', 'beautifulsoup', 'PASS')
            else:
                self.log_result('web_crawler', 'beautifulsoup', 'FAIL', 'Parsing failed')
        except Exception as e:
            self.log_result('web_crawler', 'beautifulsoup', 'FAIL', str(e)[:100])

    def validate_ai_components(self):
        """Validate AI and ML components"""
        print("\n=== AI COMPONENTS VALIDATION ===")
        
        # Test Transformers
        try:
            from transformers import pipeline
            # Quick test without downloading large models
            self.log_result('ai_components', 'transformers', 'PASS')
        except Exception as e:
            self.log_result('ai_components', 'transformers', 'FAIL', str(e)[:100])
            
        # Test FAISS
        try:
            import faiss
            index = faiss.IndexFlatL2(128)
            self.log_result('ai_components', 'faiss', 'PASS')
        except Exception as e:
            self.log_result('ai_components', 'faiss', 'FAIL', str(e)[:100])
            
        # Test LangChain
        try:
            import langchain
            self.log_result('ai_components', 'langchain', 'PASS')
        except Exception as e:
            self.log_result('ai_components', 'langchain', 'FAIL', str(e)[:100])

    def validate_api_endpoints(self):
        """Validate API framework"""
        print("\n=== API ENDPOINTS VALIDATION ===")
        
        try:
            import fastapi
            self.log_result('api_endpoints', 'fastapi', 'PASS')
        except ImportError:
            self.log_result('api_endpoints', 'fastapi', 'FAIL', 'FastAPI not available')
            
        # Check backend directory
        backend_path = Path('backend')
        if backend_path.exists():
            routes_path = backend_path / 'routes'
            if routes_path.exists():
                route_files = list(routes_path.glob('*.py'))
                self.log_result('api_endpoints', 'routes_exist', 'PASS', f"Found {len(route_files)} route files")
            else:
                self.log_result('api_endpoints', 'routes_exist', 'WARN', 'Routes directory not found')
        else:
            self.log_result('api_endpoints', 'backend_exist', 'WARN', 'Backend directory not found')

    def validate_file_operations(self):
        """Validate file and directory operations"""
        print("\n=== FILE OPERATIONS VALIDATION ===")
        
        test_dir = 'temp_test_dir'
        test_file = os.path.join(test_dir, 'test.txt')
        
        try:
            # Create directory
            os.makedirs(test_dir, exist_ok=True)
            self.log_result('file_operations', 'mkdir', 'PASS')
            
            # Write file
            with open(test_file, 'w') as f:
                f.write('test content')
            self.log_result('file_operations', 'write_file', 'PASS')
            
            # Read file
            with open(test_file, 'r') as f:
                content = f.read()
            if content == 'test content':
                self.log_result('file_operations', 'read_file', 'PASS')
            else:
                self.log_result('file_operations', 'read_file', 'FAIL', 'Content mismatch')
                
            # Cleanup
            os.remove(test_file)
            os.rmdir(test_dir)
            self.log_result('file_operations', 'cleanup', 'PASS')
            
        except Exception as e:
            self.log_result('file_operations', 'file_ops', 'FAIL', str(e)[:100])

    def validate_search_capabilities(self):
        """Validate search and indexing capabilities"""
        print("\n=== SEARCH CAPABILITIES VALIDATION ===")
        
        try:
            import faiss
            import numpy as np
            
            # Test FAISS indexing
            dimension = 128
            index = faiss.IndexFlatL2(dimension)
            
            # Add some test vectors
            vectors = np.random.random((10, dimension)).astype('float32')
            index.add(vectors)
            
            # Test search
            query = np.random.random((1, dimension)).astype('float32')
            distances, indices = index.search(query, 5)
            
            self.log_result('search_capabilities', 'faiss_search', 'PASS')
            
        except Exception as e:
            self.log_result('search_capabilities', 'faiss_search', 'FAIL', str(e)[:100])

    def validate_configuration(self):
        """Validate configuration files"""
        print("\n=== CONFIGURATION VALIDATION ===")
        
        config_files = [
            '.env',
            'config.py',
            'mam_crawler_config.py',
            'requirements.txt'
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        content = f.read()
                    self.log_result('configuration', f'{config_file}_readable', 'PASS', f"{len(content)} chars")
                except Exception as e:
                    self.log_result('configuration', f'{config_file}_readable', 'FAIL', str(e)[:100])
            else:
                self.log_result('configuration', f'{config_file}_exists', 'WARN', 'File not found')

    def run_all_validations(self):
        """Run all validation tests"""
        print("=" * 60)
        print("MAMCRAWLER PRE-DEPLOYMENT VALIDATION")
        print("=" * 60)
        
        self.validate_environment()
        self.validate_dependencies()
        self.validate_core_modules()
        self.validate_database()
        self.validate_web_crawler()
        self.validate_ai_components()
        self.validate_api_endpoints()
        self.validate_file_operations()
        self.validate_search_capabilities()
        self.validate_configuration()
        
        self.print_summary()
        
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        warnings = 0
        
        for category, tests in self.results.items():
            for test, result in tests.items():
                total_tests += 1
                if result['status'] == 'PASS':
                    passed_tests += 1
                elif result['status'] == 'FAIL':
                    failed_tests += 1
                elif result['status'] == 'WARN':
                    warnings += 1
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"Warnings: {warnings}")
        
        if failed_tests == 0:
            print("\n✓ SYSTEM READY FOR DEPLOYMENT")
        else:
            print("\n✗ CRITICAL ISSUES FOUND - REVIEW REQUIRED")
            
        # Save detailed results
        with open('validation_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nDetailed results saved to: validation_results.json")

if __name__ == '__main__':
    validator = SystemValidator()
    validator.run_all_validations()