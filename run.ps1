# VibeCatcher — One-Click Automatic Launcher
Write-Host "=====================================================" -ForegroundColor DarkYellow
Write-Host "  VibeCatcher — Reel Intelligence & DM Automation " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor DarkYellow

$ScriptDir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
Set-Location $ScriptDir

# 1. Check Python installation
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python is not installed or not in PATH! Download Python 3.10+ from python.org" -ForegroundColor Red
    Read-Host -Prompt "Press Enter to exit..."
    Exit
}

# 2. Install / verify requirements
Write-Host "[1/3] Verifying Python dependencies..." -ForegroundColor Yellow
python -m pip install -q -r requirements.txt

# 3. Install Playwright browser binaries
Write-Host "[2/3] Checking Playwright Chromium browser binaries..." -ForegroundColor Yellow
python -m playwright install chromium

# 4. Launch VibeCatcher Server & Open Browser
Write-Host "[3/3] Launching VibeCatcher Server on http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process "http://127.0.0.1:8000"
python server.py
