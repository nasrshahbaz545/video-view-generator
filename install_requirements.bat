@echo off
setlocal
cd /d "%~dp0"
title Install Video Playback Load Tester
color F0

where py >nul 2>&1
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python 3.11 or newer was not found.
    echo Install Python from python.org and select "Add Python to PATH".
    pause
    exit /b 1
  )
  set "PY=python"
)

echo Updating pip...
%PY% -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo Installing Playwright and psutil...
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo Installing Playwright Chromium and Firefox engines...
%PY% -m playwright install chromium firefox
if errorlevel 1 goto :fail

echo.
echo [OK] Installation completed. Run run_utility.bat.
pause
exit /b 0

:fail
echo.
echo [ERROR] Installation failed. Review the messages above.
pause
exit /b 1
