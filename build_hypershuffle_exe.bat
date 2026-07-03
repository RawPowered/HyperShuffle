@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title HyperShuffle EXE Builder

echo ===============================================
echo   HyperShuffle EXE Builder (PyInstaller)
echo ===============================================

rem Ensure Python exists
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [!] Python 3 not found. Install Python 3 and re-run.
  pause
  exit /b 1
)

echo [*] Ensuring build tools are available...
%PY% -m pip install --upgrade pip >nul
%PY% -m pip install pyinstaller colorama plexapi

echo [*] Building standalone HyperShuffle.exe ...
set "ICON_ARG="
if exist "icon.ico" set "ICON_ARG=--icon icon.ico"

rem Clean previous build
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist HyperShuffle.spec del /q HyperShuffle.spec

%PY% -m PyInstaller --noconfirm --onefile --clean %ICON_ARG% --name HyperShuffle --console HyperShuffle.py
set "EXITCODE=%ERRORLEVEL%"

if %EXITCODE% NEQ 0 (
  echo [!] Build failed with exit code %EXITCODE%
  pause
  exit /b %EXITCODE%
)

echo [*] Build complete! You can run: dist\HyperShuffle.exe
echo     Tip: Keep config.py alongside the EXE or embed credentials at runtime.
pause
endlocal

