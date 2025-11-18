@echo off
REM Automated Audiobookshelf Series Population Service
REM This script:
REM 1. Restarts Audiobookshelf (which repairs the database schema)
REM 2. Waits for it to start
REM 3. Runs series population via the API
REM 4. Restarts Audiobookshelf again to see changes

setlocal enabledelayedexpansion

echo ================================================================================
echo AUTOMATED AUDIOBOOKSHELF SERIES POPULATION SERVICE
echo ================================================================================
echo.

REM Get Audiobookshelf process info
echo Checking if Audiobookshelf is running...
tasklist | findstr /i "Audiobookshelf" >nul
if errorlevel 1 (
    echo Audiobookshelf is not running. Starting it now...
    REM Start Audiobookshelf (adjust path if needed)
    start "" "C:\Program Files\Audiobookshelf\Audiobookshelf.exe"
    echo Started Audiobookshelf. Waiting 10 seconds for initialization...
    timeout /t 10 /nobreak
) else (
    echo Audiobookshelf is running. Restarting to repair database schema...
    taskkill /IM "node.exe" /F 2>nul
    timeout /t 3 /nobreak
    echo Waiting for shutdown...
    timeout /t 5 /nobreak
)

echo.
echo Starting Audiobookshelf...
start "" "C:\Program Files\Audiobookshelf\Audiobookshelf.exe"

REM Wait for Audiobookshelf API to be available
echo Waiting for Audiobookshelf API to be ready (checking port 13378)...
set attempts=0
set max_attempts=30

:wait_loop
timeout /t 2 /nobreak
set /a attempts+=1

netstat -ano | findstr ":13378" >nul
if errorlevel 1 (
    if !attempts! leq !max_attempts! (
        echo  ... waiting (!attempts!/!max_attempts!)
        goto wait_loop
    ) else (
        echo ERROR: Audiobookshelf did not start in time
        exit /b 1
    )
)

echo Audiobookshelf is ready!
echo.
echo ================================================================================
echo RUNNING SERIES POPULATION
echo ================================================================================
echo.

REM Run the Python series populator
cd /d "C:\Users\dogma\Projects\MAMcrawler"
python automated_series_populator.py

if errorlevel 1 (
    echo.
    echo ERROR: Series population failed. Trying with database repair...
    python fix_db_and_populate_series.py
)

echo.
echo ================================================================================
echo RESTARTING AUDIOBOOKSHELF TO APPLY CHANGES
echo ================================================================================
echo.

echo Restarting Audiobookshelf to apply series changes...
taskkill /IM "node.exe" /F 2>nul
timeout /t 3 /nobreak

start "" "C:\Program Files\Audiobookshelf\Audiobookshelf.exe"
echo Audiobookshelf restarting...
timeout /t 5 /nobreak

echo.
echo ================================================================================
echo SERVICE COMPLETE
echo ================================================================================
echo Series should now be visible in Audiobookshelf UI
echo Check http://localhost:13378 to verify
echo.

pause
