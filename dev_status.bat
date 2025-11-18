@echo off
echo ======================================================================
echo DEVELOPMENT CONTAINER STATUS
echo ======================================================================
echo.

docker ps -a --filter "name=audiobook-catalog-dev" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo ======================================================================
echo.

docker ps -a --filter "name=audiobook-catalog-dev" | findstr "Up" >nul

if %ERRORLEVEL% EQU 0 (
    echo ✅ Container is RUNNING
    echo.
    echo You can now:
    echo   - dev_run_test.bat    ^(Run tests^)
    echo   - dev_shell.bat       ^(Open bash shell^)
    echo   - dev_python.bat      ^(Open Python REPL^)
    echo   - code .              ^(Edit in VS Code^)
) else (
    echo ⚠️  Container is NOT running
    echo.
    echo Run: dev_start.bat to start it
)

echo.
pause
