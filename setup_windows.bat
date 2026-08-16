@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_windows.ps1" %*
set "SETUP_EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%SETUP_EXIT_CODE%"=="0" (
    echo Setup failed. The window will remain open.
    echo Please send the setup.log file when asking for help.
) else (
    echo Setup finished. You can now run run_desktop.bat or run_web.bat.
)
echo.
pause
exit /b %SETUP_EXIT_CODE%
