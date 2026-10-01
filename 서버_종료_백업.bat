@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing. See LAN_TRANSFER.md for initial setup.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -X utf8 scripts\service_launcher.py stop --open-backup %*
set "SERVICE_RESULT=%ERRORLEVEL%"
pause
exit /b %SERVICE_RESULT%
