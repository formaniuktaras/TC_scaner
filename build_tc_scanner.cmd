@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%" || (
  echo [TC_SCANNER][ERROR] Failed to switch to script directory: "%SCRIPT_DIR%"
  exit /b 1
)

set "LOG_FILE=%SCRIPT_DIR%build_pyinstaller.log"
set "SPEC_FILE=%SCRIPT_DIR%TC_Scanner.spec"
set "DIST_DIR=%SCRIPT_DIR%dist\TC_Scanner"
set "BUILD_DIR=%SCRIPT_DIR%build"
set "EXE_PATH=%DIST_DIR%\TC_Scanner.exe"
set "DEFAULT_CONFIG=%DIST_DIR%\scanner_config.default.json"
set "LAST_CMD_LOG=%TEMP%\tc_scanner_build_last_cmd.log"

if exist "%LOG_FILE%" del /f /q "%LOG_FILE%" >nul 2>nul
if exist "%LAST_CMD_LOG%" del /f /q "%LAST_CMD_LOG%" >nul 2>nul

call :log "[TC_SCANNER] ===== Build started ====="
call :log "[TC_SCANNER] Start time: %DATE% %TIME%"
call :log "[TC_SCANNER] Working directory: %CD%"

call :run_and_log where py
if errorlevel 1 goto :missing_py

call :run_and_log py --version
if errorlevel 1 goto :missing_py

call :run_and_log py -m PyInstaller --version
if errorlevel 1 goto :missing_pyinstaller

if not exist "%SPEC_FILE%" (
  call :log "[TC_SCANNER][ERROR] Spec file not found: %SPEC_FILE%"
  goto :fail
)

call :log "[TC_SCANNER] Cleaning old build artifacts..."
if exist "%BUILD_DIR%" (
  rmdir /s /q "%BUILD_DIR%"
  if errorlevel 1 (
    call :log "[TC_SCANNER][ERROR] Failed to remove build directory: %BUILD_DIR%"
    goto :fail
  )
)
if exist "%DIST_DIR%" (
  rmdir /s /q "%DIST_DIR%"
  if errorlevel 1 (
    call :log "[TC_SCANNER][ERROR] Failed to remove dist directory: %DIST_DIR%"
    goto :fail
  )
)

call :log "[TC_SCANNER] Running PyInstaller build..."
call :run_and_log py -m PyInstaller --noconfirm --clean "%SPEC_FILE%"
if errorlevel 1 (
  call :log "[TC_SCANNER][ERROR] PyInstaller exited with a non-zero code."
  goto :fail
)

call :log "[TC_SCANNER] Validating build output..."
if not exist "%EXE_PATH%" (
  call :log "[TC_SCANNER][ERROR] Build failed: expected executable not found: %EXE_PATH%"
  goto :fail
)

if exist "%DEFAULT_CONFIG%" (
  call :log "[TC_SCANNER] Found bundled default config: %DEFAULT_CONFIG%"
) else (
  call :log "[TC_SCANNER][WARN] scanner_config.default.json not found in dist folder: %DEFAULT_CONFIG%"
)

call :log "[TC_SCANNER] Build SUCCESS"
call :log "[TC_SCANNER] Executable: %EXE_PATH%"
call :log "[TC_SCANNER] Build log: %LOG_FILE%"
echo.
echo [TC_SCANNER] SUCCESS: "%EXE_PATH%"
echo [TC_SCANNER] Log: "%LOG_FILE%"
exit /b 0

:missing_py
call :log "[TC_SCANNER][ERROR] Python launcher 'py' is not available in PATH."
call :log "[TC_SCANNER][ERROR] Install Python for Windows and ensure 'py' works from cmd.exe."
goto :fail

:missing_pyinstaller
call :log "[TC_SCANNER][ERROR] PyInstaller is not available for this Python launcher."
call :log "[TC_SCANNER][ERROR] Run: py -m pip install pyinstaller"
goto :fail

:fail
call :log "[TC_SCANNER] Build FAILED. See full log: %LOG_FILE%"
echo.
echo [TC_SCANNER][ERROR] Build failed. See log: "%LOG_FILE%"
exit /b 1

:run_and_log
setlocal
set "CMD=%*"
call :log "[TC_SCANNER][CMD] %CMD%"
if exist "%LAST_CMD_LOG%" del /f /q "%LAST_CMD_LOG%" >nul 2>nul
cmd /c "%CMD%" >"%LAST_CMD_LOG%" 2>&1
set "RC=%ERRORLEVEL%"
if exist "%LAST_CMD_LOG%" (
  type "%LAST_CMD_LOG%"
  type "%LAST_CMD_LOG%" >>"%LOG_FILE%"
)
endlocal & exit /b %RC%

:log
echo %~1
echo %~1>>"%LOG_FILE%"
exit /b 0
