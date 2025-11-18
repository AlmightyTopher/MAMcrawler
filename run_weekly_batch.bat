@echo off
REM Wrapper script for scheduled task
REM This ensures the virtual environment is activated

cd /d "%~dp0"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the batch downloader
python audiobook_auto_batch.py

REM Deactivate
call deactivate

REM Keep window open if error
if errorlevel 1 pause
