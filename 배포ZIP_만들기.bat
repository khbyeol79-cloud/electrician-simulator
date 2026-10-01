@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -X utf8 scripts\build_lan_release.py
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
