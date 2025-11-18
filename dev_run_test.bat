@echo off
echo Running test in development container...
echo.

docker-compose -f docker-compose.catalog.dev.yml exec audiobook-catalog-dev python audiobook_catalog_test_runner.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Test failed or container not running!
    echo Run dev_start.bat first to start the container.
    pause
    exit /b 1
)

echo.
echo ✅ Test complete! Check catalog_test_results/
pause
