@echo off
echo Stopping development container...
echo.

docker-compose -f docker-compose.catalog.dev.yml down

echo.
echo ✅ Container stopped!
pause
