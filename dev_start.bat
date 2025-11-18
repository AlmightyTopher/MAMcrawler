@echo off
echo ======================================================================
echo AUDIOBOOK CATALOG - DEVELOPMENT MODE
echo ======================================================================
echo.
echo Starting container with live code sync...
echo Edit files in VS Code, changes apply instantly in Docker!
echo.

docker-compose -f docker-compose.catalog.dev.yml up -d

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to start container!
    pause
    exit /b 1
)

echo.
echo ✅ Container started!
echo.
echo 📝 EDIT FILES:
echo    - Open this folder in VS Code
echo    - Edit audiobook_catalog_crawler.py, etc.
echo    - Changes sync automatically to Docker
echo.
echo 🚀 RUN TESTS:
echo    - dev_run_test.bat        (Run full test)
echo    - dev_shell.bat            (Open bash shell)
echo    - dev_python.bat           (Run Python interactively)
echo.
echo 🛑 STOP:
echo    - dev_stop.bat
echo.
pause
