@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title HyperShuffle Launcher

echo ===============================================
echo   HyperShuffle Launcher (Windows)
echo ===============================================

rem Check config presence early
if not exist "config.py" (
  echo [!] config.py not found. Please create it with Plex credentials.
  echo     Required: username, password, servers = ["Your Server Name"]
  echo     See README.md for details.
  echo.
  pause
  exit /b 1
)

echo [*] Checking Python...
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [!] Python 3 not found. Please install from https://www.python.org/downloads/
  pause
  exit /b 1
)

echo [*] Creating/using virtual environment (.venv)...
%PY% -m venv .venv >nul 2>nul
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
) else (
  echo [!] Failed to create virtual environment.
  pause
  exit /b 1
)

echo [*] Upgrading pip and installing dependencies...
python -m pip install --upgrade pip >nul
if exist requirements.txt (
  pip install -r requirements.txt
) else (
  echo [*] requirements.txt not found, installing core packages...
  pip install colorama plexapi
)

echo [*] Launching HyperShuffle...
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
python HyperShuffle.py
set "EXITCODE=%ERRORLEVEL%"

echo.
echo [*] HyperShuffle exited with code %EXITCODE%
echo     Tip: Keep this window open to see any errors above.
pause
endlocal

