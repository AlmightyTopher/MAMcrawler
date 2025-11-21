#!/usr/bin/env python3
"""
Dependency Recovery and Fix Script
Repairs corrupted dependencies and resolves import conflicts
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run command with error handling"""
    print(f"\n[REPAIR] {description}")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[SUCCESS] {description} completed")
            return True
        else:
            print(f"[ERROR] {description} failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] {description} exception: {e}")
        return False

def fix_dependencies():
    """Fix corrupted dependencies"""
    print("=" * 60)
    print("MAMCRAWLER DEPENDENCY RECOVERY")
    print("=" * 60)
    
    # Step 1: Upgrade pip
    run_command("venv\\Scripts\\python.exe -m pip install --upgrade pip", "Upgrading pip")
    
    # Step 2: Clear problematic packages
    problematic_packages = [
        "pydantic-core",
        "regex", 
        "numpy",
        "faiss-cpu",
        "torch",
        "transformers",
        "langchain"
    ]
    
    for package in problematic_packages:
        run_command(f"venv\\Scripts\\pip.exe uninstall {package} -y", f"Uninstalling {package}")
    
    # Step 3: Clear pip cache
    run_command("venv\\Scripts\\pip.exe cache purge", "Clearing pip cache")
    
    # Step 4: Install dependencies in correct order
    core_deps = [
        "pydantic-core",
        "numpy",
        "faiss-cpu", 
        "pydantic",
        "fastapi",
        "uvicorn"
    ]
    
    for dep in core_deps:
        run_command(f"venv\\Scripts\\pip.exe install {dep}", f"Installing {dep}")
    
    # Step 5: Install AI/ML dependencies
    ai_deps = [
        "torch",
        "transformers", 
        "langchain",
        "sentence-transformers"
    ]
    
    for dep in ai_deps:
        run_command(f"venv\\Scripts\\pip.exe install {dep}", f"Installing {dep}")
    
    # Step 6: Reinstall web scraping dependencies
    web_deps = [
        "beautifulsoup4",
        "crawl4ai",
        "playwright"
    ]
    
    for dep in web_deps:
        run_command(f"venv\\Scripts\\pip.exe install {dep}", f"Installing {dep}")
    
    # Step 7: Fix playwright browsers
    run_command("venv\\Scripts\\playwright.exe install chromium", "Installing Playwright browsers")
    
    print("\n" + "=" * 60)
    print("DEPENDENCY REPAIR COMPLETE")
    print("=" * 60)
    print("Run validation again to check results")

if __name__ == '__main__':
    fix_dependencies()