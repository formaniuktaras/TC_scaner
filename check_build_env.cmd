@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%" || (
  echo [TC_SCANNER][ERROR] Failed to switch to script directory: "%SCRIPT_DIR%"
  exit /b 1
)

echo [TC_SCANNER] ===== Build environment diagnostics =====
echo [TC_SCANNER] Working directory: %CD%
echo.

echo [TC_SCANNER][CMD] where py
where py
if errorlevel 1 echo [TC_SCANNER][WARN] 'py' not found in PATH.
echo.

echo [TC_SCANNER][CMD] py --version
py --version
if errorlevel 1 echo [TC_SCANNER][WARN] Unable to read Python version via 'py'.
echo.

echo [TC_SCANNER][CMD] py -m PyInstaller --version
py -m PyInstaller --version
if errorlevel 1 echo [TC_SCANNER][WARN] PyInstaller not available for this 'py'.
echo.

call :check_file "TC_Scanner.spec"
call :check_file "launch_tc_scanner.pyw"
call :check_file "scanner_config.default.json"

echo.
echo [TC_SCANNER] Diagnostics completed.
exit /b 0

:check_file
if exist "%~1" (
  echo [TC_SCANNER][OK] Found: %~1
) else (
  echo [TC_SCANNER][ERROR] Missing: %~1
)
exit /b 0
