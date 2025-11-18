@echo off
echo ======================================================================
echo AUDIOBOOK CATALOG CRAWLER - DOCKER TEST
echo ======================================================================
echo.

echo [1/3] Building Docker image...
docker-compose -f docker-compose.catalog.yml build

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker build failed!
    pause
    exit /b 1
)

echo.
echo [2/3] Running comprehensive test...
docker-compose -f docker-compose.catalog.yml up

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Test execution failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Viewing results...
echo.
echo Test results saved to:
echo - catalog_test_results\
echo.
dir /b catalog_test_results\*.json 2>nul
dir /b catalog_test_results\*.csv 2>nul
dir /b catalog_test_results\*.md 2>nul
echo.

echo ======================================================================
echo TEST COMPLETE
echo ======================================================================
echo.
echo View reports in: catalog_test_results\
echo View logs: audiobook_catalog_test.log
echo View screenshots: catalog_cache\*.png
echo.
pause
