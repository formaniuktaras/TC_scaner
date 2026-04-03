@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

where pyinstaller >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo [TC_SCANNER] PyInstaller not found. Install it first: py -m pip install pyinstaller
  exit /b 1
)

pyinstaller --noconfirm --clean --onefile --windowed --name TC_Scanner launch_tc_scanner.pyw
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

echo [TC_SCANNER] Build complete: "%SCRIPT_DIR%dist\TC_Scanner.exe"
exit /b 0
