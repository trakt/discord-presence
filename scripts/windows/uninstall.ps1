# Trakt Discord Presence - Windows Uninstaller Script  
# This script removes the Trakt Discord Presence scheduled task

# Get script directory and project directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$TaskName = "Trakt-Discord-Presence"

Write-Host "🗑️  Trakt Discord Presence - Windows Uninstaller" -ForegroundColor Red
Write-Host "================================================" -ForegroundColor Red
Write-Host ""

# Check if the task exists
try {
    $Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $Task) {
        Write-Host "ℹ️  Task not found. Nothing to uninstall." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "📁 Project files remain at: $ProjectDir" -ForegroundColor White
        Write-Host "🔄 To reinstall the task, run: .\scripts\install.ps1" -ForegroundColor White
        exit 0
    }
} catch {
    Write-Host "ℹ️  Task not found. Nothing to uninstall." -ForegroundColor Yellow
    exit 0
}

# Stop the task if running
Write-Host "⏹️  Stopping task..." -ForegroundColor Yellow
try {
    $TaskState = (Get-ScheduledTask -TaskName $TaskName).State
    if ($TaskState -eq "Running") {
        Stop-ScheduledTask -TaskName $TaskName
        Write-Host "   Task stopped." -ForegroundColor Green
    } else {
        Write-Host "   Task was not running." -ForegroundColor White
    }
} catch {
    Write-Host "   Could not stop task (may not be running)." -ForegroundColor Yellow
}

# Remove the task
Write-Host "🗂️  Removing scheduled task..." -ForegroundColor Yellow
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "✅ Task successfully removed!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to remove task: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 You can manually remove it using Task Scheduler:" -ForegroundColor Cyan
    Write-Host "   1. Press Win+R, type 'taskschd.msc'" -ForegroundColor White
    Write-Host "   2. Find and delete '$TaskName'" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "📁 Project files remain at: $ProjectDir" -ForegroundColor White
Write-Host "   • Python code and configuration are untouched" -ForegroundColor White
Write-Host "   • Virtual environment (.venv) is preserved" -ForegroundColor White
Write-Host "   • Log files are preserved in logs\ directory" -ForegroundColor White
Write-Host ""
Write-Host "🔄 To reinstall the task, run: .\scripts\install.ps1" -ForegroundColor White
Write-Host ""
Write-Host "🗑️  To completely remove the project:" -ForegroundColor Red
Write-Host "   Remove-Item -Recurse -Force `"$ProjectDir`"" -ForegroundColor White