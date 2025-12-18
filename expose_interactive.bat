@echo off
setlocal
cls

echo ==================================================
echo      Cloudflare Tunnel Exposer
echo ==================================================
echo.

:ASK_NAME
set /p SUBDOMAIN="Enter the SUBDOMAIN name (e.g., 'myapp' for myapp.tophertek.com): "
if "%SUBDOMAIN%"=="" goto ASK_NAME

:ASK_PORT
set /p PORT="Enter the LOCAL PORT number (e.g., 3000): "
if "%PORT%"=="" goto ASK_PORT

echo.
echo --------------------------------------------------
echo Configuration:
echo   Domain: https://%SUBDOMAIN%.tophertek.com
echo   Local : http://localhost:%PORT%
echo --------------------------------------------------
echo.
set /p CONFIRM="Is this correct? (Y/N): "
if /i not "%CONFIRM%"=="Y" goto END

echo.
echo Running configuration script...
echo.

python c:\Users\dogma\Projects\MAMcrawler\add_tunnel_route.py %SUBDOMAIN% %PORT%

pause

:END
endlocal
