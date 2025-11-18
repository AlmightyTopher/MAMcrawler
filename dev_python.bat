@echo off
echo Opening Python interpreter in development container...
echo.

docker-compose -f docker-compose.catalog.dev.yml exec audiobook-catalog-dev python

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Container not running!
    echo Run dev_start.bat first to start the container.
    pause
    exit /b 1
)
