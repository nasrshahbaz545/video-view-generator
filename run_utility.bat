@echo off
setlocal
cd /d "%~dp0"
title Video Playback Load Tester
color F0

where py >nul 2>&1
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python 3.11 or newer was not found.
    echo Install Python, select "Add Python to PATH", then run install_requirements.bat.
    pause
    exit /b 1
  )
  set "PY=python"
)

%PY% main.py
set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" echo Utility finished with exit code %RC%.
pause
exit /b %RC%
