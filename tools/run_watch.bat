@echo off
REM Loads SMTP credentials from data\config\smtp.env (if present) and runs
REM the weekly product watch. Intended to be invoked by Windows Task
REM Scheduler every Sunday - see docs\scheduling.md.
setlocal enabledelayedexpansion

set "ROOT=%~dp0.."
set "ENV_FILE=%ROOT%\data\config\smtp.env"

if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
        set "%%A=%%B"
    )
)

set PYTHONIOENCODING=utf-8

"%ROOT%\.venv\Scripts\python.exe" -m lidl_tracker.cli_watch ^
    --query "queso en salmuera" ^
    --to "%LIDL_WATCH_TO%" ^
    >> "%ROOT%\data\watch.log" 2>&1
