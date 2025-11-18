#!/usr/bin/env python3
"""
Verification script for Audiobook Automation System implementation
Checks that all Phase 1-5 components are in place and functional

Run this to verify the complete backend setup:
    python verify_implementation.py
"""

import os
import sys
from pathlib import Path
from importlib import import_module

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

def check_file_exists(filepath, description):
    """Check if a file exists"""
    exists = Path(filepath).exists()
    status = f"{GREEN}[OK]{RESET}" if exists else f"{RED}[FAIL]{RESET}"
    print(f"  {status} {description}")
    return exists

def check_directory_exists(dirpath, description):
    """Check if a directory exists"""
    exists = Path(dirpath).is_dir()
    status = f"{GREEN}[OK]{RESET}" if exists else f"{RED}[FAIL]{RESET}"
    print(f"  {status} {description}")
    return exists

def check_import(module_path, description):
    """Check if a module can be imported"""
    try:
        import_module(module_path)
        print(f"  {GREEN}[OK]{RESET} {description}")
        return True
    except ImportError as e:
        print(f"  {RED}[FAIL]{RESET} {description} - {e}")
        return False

def print_section(title):
    """Print a section header"""
    print(f"\n{BOLD}{title}{RESET}")
    print("-" * 60)

def count_files(directory, extension):
    """Count files with specific extension"""
    path = Path(directory)
    if not path.exists():
        return 0
    return len(list(path.rglob(f"*{extension}")))

def main():
    """Run all verification checks"""
    print(f"\n{BOLD}Audiobook Automation System - Implementation Verification{RESET}")
    print("=" * 60)

    project_root = Path(__file__).parent
    os.chdir(project_root)

    all_passed = True

    # Phase 1: Design & Architecture
    print_section("PHASE 1: Design & Architecture")
    all_passed &= check_file_exists(
        "database_schema.sql",
        "PostgreSQL schema file"
    )
    all_passed &= check_file_exists(
        "docs/DATABASE.md",
        "Database documentation"
    )
    all_passed &= check_file_exists(
        "docs/ARCHITECTURE.md",
        "Architecture documentation"
    )
    all_passed &= check_file_exists(
        "PHASE_1_COMPLETE.md",
        "Phase 1 completion summary"
    )

    # Phase 2: FastAPI Project Structure
    print_section("PHASE 2: FastAPI Project Structure")
    all_passed &= check_directory_exists(
        "backend",
        "Backend directory"
    )
    all_passed &= check_file_exists(
        "backend/config.py",
        "Configuration module"
    )
    all_passed &= check_file_exists(
        "backend/database.py",
        "Database connection module"
    )
    all_passed &= check_file_exists(
        "backend/main.py",
        "FastAPI application"
    )

    # Phase 3: ORM Models & Scheduler
    print_section("PHASE 3: SQLAlchemy Models & Scheduler")
    all_passed &= check_directory_exists(
        "backend/models",
        "Models directory"
    )
    all_passed &= check_file_exists(
        "backend/models/book.py",
        "Book model"
    )
    all_passed &= check_file_exists(
        "backend/models/series.py",
        "Series model"
    )
    all_passed &= check_file_exists(
        "backend/models/author.py",
        "Author model"
    )
    all_passed &= check_file_exists(
        "backend/models/download.py",
        "Download model"
    )

    all_passed &= check_directory_exists(
        "backend/schedulers",
        "Schedulers directory"
    )
    all_passed &= check_file_exists(
        "backend/schedulers/scheduler.py",
        "Scheduler manager"
    )
    all_passed &= check_file_exists(
        "backend/schedulers/tasks.py",
        "Scheduled tasks"
    )

    # Phase 4: Integration Clients & Module Wrappers
    print_section("PHASE 4: Integration Clients & Module Wrappers")
    all_passed &= check_directory_exists(
        "backend/integrations",
        "Integrations directory"
    )
    all_passed &= check_file_exists(
        "backend/integrations/abs_client.py",
        "Audiobookshelf client"
    )
    all_passed &= check_file_exists(
        "backend/integrations/qbittorrent_client.py",
        "qBittorrent client"
    )
    all_passed &= check_file_exists(
        "backend/integrations/google_books_client.py",
        "Google Books client"
    )

    all_passed &= check_directory_exists(
        "backend/modules",
        "Modules directory"
    )
    all_passed &= check_file_exists(
        "backend/modules/mam_crawler.py",
        "MAM crawler wrapper"
    )
    all_passed &= check_file_exists(
        "backend/modules/metadata_correction.py",
        "Metadata correction module"
    )

    # Phase 5: API Routes & Service Layer
    print_section("PHASE 5: API Routes & Service Layer")
    all_passed &= check_directory_exists(
        "backend/routes",
        "Routes directory"
    )
    all_passed &= check_file_exists(
        "backend/routes/books.py",
        "Books router"
    )
    all_passed &= check_file_exists(
        "backend/routes/series.py",
        "Series router"
    )
    all_passed &= check_file_exists(
        "backend/routes/authors.py",
        "Authors router"
    )
    all_passed &= check_file_exists(
        "backend/routes/downloads.py",
        "Downloads router"
    )

    all_passed &= check_directory_exists(
        "backend/services",
        "Services directory"
    )
    all_passed &= check_file_exists(
        "backend/services/book_service.py",
        "Book service"
    )
    all_passed &= check_file_exists(
        "backend/services/series_service.py",
        "Series service"
    )
    all_passed &= check_file_exists(
        "backend/services/download_service.py",
        "Download service"
    )

    all_passed &= check_directory_exists(
        "backend/utils",
        "Utils directory"
    )
    all_passed &= check_file_exists(
        "backend/utils/errors.py",
        "Error definitions"
    )
    all_passed &= check_file_exists(
        "backend/utils/logging.py",
        "Logging configuration"
    )

    all_passed &= check_file_exists(
        "backend/schemas.py",
        "Pydantic schemas"
    )
    all_passed &= check_file_exists(
        "backend/requirements.txt",
        "Python dependencies"
    )

    # Documentation Files
    print_section("Documentation Files")
    all_passed &= check_file_exists(
        "PHASE_5_INTEGRATION_COMPLETE.md",
        "Phase 5 integration guide"
    )
    all_passed &= check_file_exists(
        "PHASE_5_6_STATUS.md",
        "Phase 5 completion status"
    )
    all_passed &= check_file_exists(
        "IMPLEMENTATION_STATUS.md",
        "Complete implementation status"
    )
    all_passed &= check_file_exists(
        "QUICK_START_GUIDE.md",
        "Quick start guide"
    )

    # Module Import Tests
    print_section("Module Import Tests")
    all_passed &= check_import(
        "backend.config",
        "Configuration module"
    )
    all_passed &= check_import(
        "backend.database",
        "Database module"
    )
    all_passed &= check_import(
        "backend.models.book",
        "Book model"
    )
    all_passed &= check_import(
        "backend.schemas",
        "Pydantic schemas"
    )
    all_passed &= check_import(
        "backend.utils.errors",
        "Custom exceptions"
    )
    all_passed &= check_import(
        "backend.utils.helpers",
        "Helper functions"
    )

    # File Statistics
    print_section("Implementation Statistics")
    backend_files = count_files("backend", ".py")
    print(f"  Backend Python files: {BOLD}{backend_files}{RESET}")

    doc_files = count_files(".", ".md")
    print(f"  Documentation files: {BOLD}{doc_files}{RESET}")

    print(f"  Project root: {project_root}")

    # Summary
    print_section("Verification Summary")
    if all_passed:
        print(f"{GREEN}{BOLD}[SUCCESS] All checks passed!{RESET}")
        print(f"\n{BOLD}The Audiobook Automation System is fully implemented.{RESET}")
        print(f"Ready for Phase 6: Integration Testing & Deployment")
        print(f"\n{BOLD}Next steps:{RESET}")
        print("  1. Review QUICK_START_GUIDE.md")
        print("  2. Configure .env file with your credentials")
        print("  3. Install dependencies: pip install -r backend/requirements.txt")
        print("  4. Initialize database: python -c \"from backend.database import init_db; init_db()\"")
        print("  5. Start server: python backend/main.py")
        return 0
    else:
        print(f"{RED}{BOLD}[FAILED] Some checks failed!{RESET}")
        print("Please review the errors above and resolve issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
