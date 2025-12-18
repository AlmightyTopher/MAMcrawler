@echo off
echo ======================================================================
echo STARTING UNIFIED MAMCRAWLER SYSTEM
echo ======================================================================
echo.
echo Dashboard: http://localhost:8081
echo API Docs:  http://localhost:8081/docs
echo.
echo Press Ctrl+C to stop.
echo.

uvicorn backend.main:app --host 127.0.0.1 --port 8081 --reload

pause
