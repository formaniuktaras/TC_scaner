@echo off
setlocal

REM DEBUG launcher (console expected).
REM GUI-only launchers: TC_Scanner.exe (preferred) or launch_tc_scanner_silent.vbs via wscript.exe.

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

echo [TC_SCANNER][DEBUG] Console Python launcher not found.
echo [TC_SCANNER][DEBUG] For GUI-only run use: TC_Scanner.exe or wscript.exe launch_tc_scanner_silent.vbs "%%P"
exit /b 1
