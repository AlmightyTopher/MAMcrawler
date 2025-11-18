@echo off
REM Automated Audiobookshelf Series Population with Safe Restart
REM This script:
REM 1. Starts Audiobookshelf (which auto-repairs the database schema)
REM 2. Waits for it to fully initialize
REM 3. Stops Audiobookshelf
REM 4. Runs the series populator
REM 5. Restarts Audiobookshelf to see the changes

setlocal enabledelayedexpansion

echo.
echo ================================================================================
echo AUDIOBOOKSHELF RESTART AND SERIES POPULATION
echo ================================================================================
echo.

REM Step 1: Start Audiobookshelf to repair schema
echo Step 1: Starting Audiobookshelf (this will repair the database schema)...
echo.

REM Try common paths
if exist "C:\Program Files\Audiobookshelf\Audiobookshelf.exe" (
    start "" "C:\Program Files\Audiobookshelf\Audiobookshelf.exe"
    echo Started from C:\Program Files
) else if exist "C:\Program Files (x86)\Audiobookshelf\Audiobookshelf.exe" (
    start "" "C:\Program Files (x86)\Audiobookshelf\Audiobookshelf.exe"
    echo Started from C:\Program Files (x86)
) else (
    echo ERROR: Could not find Audiobookshelf executable
    echo Please install Audiobookshelf or verify the path
    exit /b 1
)

REM Wait for Audiobookshelf to start and repair database
echo.
echo Waiting for Audiobookshelf to initialize (30 seconds)...
timeout /t 30 /nobreak

REM Step 2: Stop Audiobookshelf
echo.
echo Step 2: Stopping Audiobookshelf (to allow database access)...
taskkill /IM node.exe /F 2>nul
timeout /t 2 /nobreak

REM Step 3: Run series populator
echo.
echo Step 3: Populating series in the database...
cd /d "C:\Users\dogma\Projects\MAMcrawler"
python simple_series_populator.py

if errorlevel 1 (
    echo.
    echo ERROR: Series population failed
    echo Check simple_series_populator.log for details
    exit /b 1
)

REM Step 4: Restart Audiobookshelf
echo.
echo Step 4: Restarting Audiobookshelf to apply changes...
timeout /t 2 /nobreak

if exist "C:\Program Files\Audiobookshelf\Audiobookshelf.exe" (
    start "" "C:\Program Files\Audiobookshelf\Audiobookshelf.exe"
    echo Started from C:\Program Files
) else if exist "C:\Program Files (x86)\Audiobookshelf\Audiobookshelf.exe" (
    start "" "C:\Program Files (x86)\Audiobookshelf\Audiobookshelf.exe"
    echo Started from C:\Program Files (x86)
)

echo.
echo ================================================================================
echo COMPLETE
echo ================================================================================
echo.
echo Waiting for Audiobookshelf to start (30 seconds)...
timeout /t 30 /nobreak

echo.
echo Series should now be visible in Audiobookshelf!
echo Open http://localhost:13378 to verify
echo.
echo ================================================================================
pause
