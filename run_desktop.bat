@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_desktop.ps1"
exit /b %ERRORLEVEL%

