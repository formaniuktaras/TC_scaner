@echo off
setlocal

REM Launch wrapper for Total Commander button.
REM Usage from TC parameters: "%P"

set "SCRIPT_DIR=%~dp0"
set "TARGET_DIR=%~1"

if "%TARGET_DIR%"=="" set "TARGET_DIR=%CD%"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%SCRIPT_DIR%tc_scanner_launcher.py" "%TARGET_DIR%"
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python "%SCRIPT_DIR%tc_scanner_launcher.py" "%TARGET_DIR%"
  exit /b %ERRORLEVEL%
)

echo [TC_SCANER] Python launcher was not found in PATH.
echo Install Python 3.10+ and ensure python.exe or py.exe is available.
exit /b 1
