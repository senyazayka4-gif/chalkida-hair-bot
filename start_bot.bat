@echo off
title Chalkida Hair Bot Launcher
echo ===================================================
echo   💇‍♀️ Launching Chalkida Hair Bot (Local Session) 💇‍♀️
echo ===================================================
echo.
echo Connecting to Cloud Supabase Database...
echo Checking local Python environment...
py -3 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org and try again.
    pause
    exit /b
)
echo.
echo Running Zenith Chalkida Hair Bot...
py main.py
echo.
echo Bot stopped.
pause
