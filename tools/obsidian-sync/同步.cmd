@echo off
setlocal
cd /d "%~dp0"

rem ---------------------------------------------------------------------------
rem  Double-click to pull the latest daily reports into this Obsidian vault.
rem
rem  All Chinese output lives in 同步.py - Python prints Unicode correctly to the
rem  Windows console. This wrapper stays pure ASCII on purpose: a .bat file is
rem  parsed with the OEM code page, so UTF-8 Chinese in here breaks the parser.
rem  Keep this file saved as GBK anyway, because the script name below is Chinese.
rem
rem  Python lookup, in order:
rem    1) python on PATH
rem    2) the managed install, version read from the "current" marker file
rem    3) any version directory that has a python.exe
rem ---------------------------------------------------------------------------

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

echo [ERROR] Python not found. Install Python 3.10+ and run this again.
goto end

:run
"%PY%" "%~dp0同步.py" %*
if errorlevel 1 echo [ERROR] Sync did not complete - see the message above.

:end
echo.
pause
