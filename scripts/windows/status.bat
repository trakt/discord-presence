@echo off
:: Trakt Discord Presence - Windows Status Checker Wrapper
:: This batch file runs the PowerShell status checker script

echo 📊 Trakt Discord Presence - Windows Status
echo ===========================================
echo.

:: Check if PowerShell is available
powershell -Command "Write-Host 'PowerShell is available'" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ PowerShell is not available or not in PATH
    echo    This script requires PowerShell 5.0 or later
    pause
    exit /b 1
)

:: Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

:: Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%status.ps1"

echo.
echo Press any key to continue...
pause >nul