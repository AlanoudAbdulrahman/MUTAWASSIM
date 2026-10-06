@echo off
rem Mutawassim: double-click to start the website (Windows).
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
    set "PY=venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)
set PYTHONIOENCODING=utf-8
"%PY%" -m mutawassim %*
pause
