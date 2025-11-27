@echo off
REM VPN Port Proxy Setup for qBittorrent
REM This script requires Administrator privileges

echo ================================
echo VPN Port Proxy Setup
echo ================================
echo.

REM Check for administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator!
    echo Please right-click this file and select "Run as Administrator"
    pause
    exit /b 1
)

echo Running as Administrator: OK
echo.

REM Step 1: Clean up existing proxy
echo [1] Cleaning up existing proxy configurations...
for /f "tokens=*" %%A in ('netsh interface portproxy show all ^| find "1080"') do (
    echo Found existing proxy on port 1080, removing...
    netsh interface portproxy delete v4tov4 listenport=1080 listenaddress=127.0.0.1
)
timeout /t 2 /nobreak

REM Step 2: Create new port proxy
echo [2] Creating new port proxy (127.0.0.1:1080 -^> 10.2.0.1:8080)...
netsh interface portproxy add v4tov4 listenport=1080 listenaddress=127.0.0.1 connectport=8080 connectaddress=10.2.0.1
if %errorLevel% equ 0 (
    echo Port proxy created successfully
) else (
    echo Failed to create port proxy
    pause
    exit /b 1
)

timeout /t 2 /nobreak

REM Step 3: Verify proxy
echo [3] Verifying port proxy configuration...
netsh interface portproxy show all | find "1080"
if %errorLevel% equ 0 (
    echo Proxy verified successfully
) else (
    echo Failed to verify proxy
    pause
    exit /b 1
)

echo.
echo ================================
echo Next Steps:
echo ================================
echo.
echo Configure qBittorrent:
echo   1. Open qBittorrent
echo   2. Tools -^> Options -^> Network
echo   3. Proxy Server:
echo      - Type: SOCKS5
echo      - IP Address: 127.0.0.1
echo      - Port: 1080
echo   4. Check: "Use proxy for peer connections"
echo   5. Click OK
echo.
echo Test Connection:
echo   Run: python check_vpn_connection.py
echo.
pause
