@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_windows.ps1" -WebOnly
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
