@echo off
:: Trakt Discord Presence - Windows Installer Wrapper
:: This batch file runs the PowerShell installer script

echo 🎬 Trakt Discord Presence - Windows Installer
echo ===============================================
echo.

:: Check if PowerShell is available
powershell -Command "Write-Host 'PowerShell is available'" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ PowerShell is not available or not in PATH
    echo    This script requires PowerShell 5.0 or later
    echo    Please install PowerShell or run from PowerShell directly
    pause
    exit /b 1
)

:: Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

:: Run the PowerShell script
echo 🚀 Running PowerShell installer...
echo.
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install.ps1"

:: Check the result
if %errorlevel% equ 0 (
    echo.
    echo ✅ Installation completed successfully!
) else (
    echo.
    echo ❌ Installation failed with error code %errorlevel%
    echo.
    echo 💡 Troubleshooting tips:
    echo    • Try running as Administrator
    echo    • Check if PowerShell execution policy allows scripts
    echo    • Run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
)

echo.
echo Press any key to continue...
pause >nul