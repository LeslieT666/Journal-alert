@echo off
setlocal
cd /d "%~dp0"

rem ---------------------------------------------------------------------------
rem  Scheduled-task entry point. Same job as the double-click launcher in this
rem  folder, but built for silence:
rem    - no "pause"  (a scheduled task has no console; pause would hang forever)
rem    - no Chinese (batch files are parsed with the OEM code page - mixing in
rem                    UTF-8 Chinese can break the parser on another machine)
rem    - output goes to .sync.log next to this file instead of a console
rem
rem  Registered as the Windows task "JournalAlertObsidianSync".
rem  Keep the log name starting with a dot: Obsidian ignores dot-files, so it
rem  will not show up in your vault's file list or search.
rem ---------------------------------------------------------------------------

set "LOG=%~dp0.sync.log"
set "PY="
set "PYROOT=C:\Users\wangs\.workbuddy\binaries\python\versions"

where python >nul 2>nul && set "PY=python"
if defined PY goto run

set "PYVER="
if exist "%PYROOT%\current" set /p PYVER=<"%PYROOT%\current"
if defined PYVER if exist "%PYROOT%\%PYVER%\python.exe" set "PY=%PYROOT%\%PYVER%\python.exe"
if defined PY goto run

for /d %%d in ("%PYROOT%\*") do if exist "%%d\python.exe" set "PY=%%d\python.exe"
if defined PY goto run

echo [%DATE% %TIME%] ERROR - Python not found. >> "%LOG%"
exit /b 2

:run
rem Keep the log from growing forever (roughly ten years of runs, then cycle).
for %%A in ("%LOG%") do if %%~zA GTR 524288 del "%LOG%"

rem Only Python writes to the log (the --stamp flag makes it print the run
rem timestamp). Do NOT add "echo" lines here: batch echoes come out in the OEM
rem code page while Python uses its own encoding, and a log with both in it
rem cannot be decoded by either.
echo. >> "%LOG%"
"%PY%" "%~dp0sync_reports.py" --stamp >> "%LOG%" 2>&1
exit /b %ERRORLEVEL%
