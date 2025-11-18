@echo off
echo ========================================
echo Testing Automated Batch System
echo ========================================
echo.
echo This will test the batch downloader in DRY-RUN mode.
echo No actual downloads will be performed.
echo.
pause

cd /d "%~dp0"

echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Running automated batch (DRY-RUN)...
echo.
python audiobook_auto_batch.py --dry-run

echo.
echo ========================================
echo Test Complete!
echo ========================================
echo.
echo Check the output above for:
echo   - Genres processed
echo   - Audiobooks found
echo   - What would have been downloaded
echo.
echo Review files:
echo   - audiobook_auto.log (detailed log)
echo   - batch_report_*.txt (summary report)
echo   - batch_stats_*.json (detailed stats)
echo.
pause
