@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
rem Edit ONLY the backup ZIP filename/path below. Keep the quotation marks.
set "BACKUP_FILE=user-data-backups\YOUR_BACKUP_FILENAME.zip"
if not exist ".venv\Scripts\python.exe" (
  echo Run the initial server setup BAT first. See LAN_TRANSFER.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -X utf8 scripts\restore_service_backup.py "%BACKUP_FILE%"
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
