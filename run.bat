@echo off
title VibeCatcher Launcher
echo =====================================================
echo   VibeCatcher -- Reel Intelligence ^& DM Automation
echo =====================================================
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File run.ps1
pause
