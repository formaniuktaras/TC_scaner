@echo off
setlocal

REM GUI launcher shim for Total Commander.
REM Delegates to VBS silent launcher to avoid persistent console window.

set "SCRIPT_DIR=%~dp0"
set "TARGET_DIR=%~1"
if "%TARGET_DIR%"=="" set "TARGET_DIR=%CD%"

set "VBS_LAUNCHER=%SCRIPT_DIR%launch_tc_scanner_silent.vbs"
if not exist "%VBS_LAUNCHER%" (
  echo [TC_SCANNER] Missing launcher: "%VBS_LAUNCHER%"
  exit /b 1
)

wscript.exe //nologo "%VBS_LAUNCHER%" "%TARGET_DIR%"
exit /b %ERRORLEVEL%
