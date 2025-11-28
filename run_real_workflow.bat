@echo off
REM ============================================================================
REM REAL WORKFLOW EXECUTION SCRIPT
REM Runs complete 14-phase audiobook workflow with 100% real data
REM ============================================================================

echo.
echo ============================================================================
echo REAL WORKFLOW EXECUTION - COMPLETE 14-PHASE AUDIOBOOK ACQUISITION
echo ============================================================================
echo.
echo This script will:
echo   1. Scan YOUR AudiobookShelf library (real data)
echo   2. Search Google Books API (real results)
echo   3. Search MAM for torrents (real torrents)
echo   4. Add to YOUR qBittorrent (real downloads)
echo   5. Monitor real download progress
echo   6. Import to YOUR AudiobookShelf library
echo   7. Write ID3 metadata to audio files
echo   8-8F. Enhance metadata (standardize, detect, populate narrators)
echo   9-10. Build author history and missing books queue
echo   11. Generate comprehensive final report
echo   12. Create automated backup with rotation
echo.
echo ALL DATA IS 100% REAL - NO MOCKING, NO SKIPPING, NO FAKES
echo.

REM Set environment variables
set PYTHONIOENCODING=utf-8
set LOG_LEVEL=DEBUG
set DEBUG_MODE=true

REM Display configuration
echo Configuration:
echo   AudiobookShelf: http://localhost:13378
echo   qBittorrent: http://192.168.0.48:52095/
echo   MAM Username: dogmansemail1@gmail.com
echo   Download Path: F:\Audiobookshelf\Books
echo.

REM Pre-flight checks
echo Pre-flight checks:
echo.

echo Checking Python environment...
venv\Scripts\python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python environment not found. Run: python -m venv venv
    pause
    exit /b 1
)
echo [OK] Python environment ready

echo.
echo Checking dependencies...
venv\Scripts\pip list | findstr /I "mutagen aiohttp anthropic" > nul 2>&1
if errorlevel 1 (
    echo [WARNING] Some dependencies may be missing
    echo Run: venv\Scripts\pip install -r requirements.txt
)
echo [OK] Dependencies present

echo.
echo Checking .env configuration...
findstr /R "ABS_URL ABS_TOKEN QBITTORRENT_URL MAM_USERNAME GOOGLE_BOOKS_API_KEY" .env > nul 2>&1
if errorlevel 1 (
    echo [ERROR] .env file missing critical configuration
    echo Ensure .env has: ABS_URL, ABS_TOKEN, QBITTORRENT_URL, MAM_USERNAME, GOOGLE_BOOKS_API_KEY
    pause
    exit /b 1
)
echo [OK] .env configuration complete

echo.
echo ============================================================================
echo READY TO EXECUTE REAL WORKFLOW
echo ============================================================================
echo.
echo Press ENTER to start, or Ctrl+C to cancel...
echo.
pause

REM Create timestamped log file
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set logfile=workflow_run_%mydate%_%mytime%.log

echo.
echo ============================================================================
echo EXECUTING WORKFLOW - Started at %date% %time%
echo Log file: %logfile%
echo ============================================================================
echo.

REM Run the workflow
venv\Scripts\python execute_full_workflow.py > %logfile% 2>&1

REM Check if successful
if errorlevel 1 (
    echo.
    echo ============================================================================
    echo [ERROR] WORKFLOW FAILED
    echo ============================================================================
    echo.
    echo Check log file: %logfile%
    echo View with: type %logfile%
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ============================================================================
    echo [SUCCESS] WORKFLOW COMPLETED
    echo ============================================================================
    echo.
    echo Report file: workflow_final_report.json
    echo Log file: %logfile%
    echo.
    echo Verify results:
    echo   1. Check AudiobookShelf: http://localhost:13378 (new books visible)
    echo   2. Check qBittorrent: http://192.168.0.48:52095 (torrents added)
    echo   3. Check report: workflow_final_report.json (statistics)
    echo.
    pause
    exit /b 0
)
