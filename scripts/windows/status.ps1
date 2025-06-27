# Trakt Discord Presence - Windows Status Checker
# This script checks the status of the scheduled task and shows recent logs

# Get script directory and project directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$LogsDir = Join-Path $ProjectDir "logs"
$TaskName = "Trakt-Discord-Presence"
$EnvFile = Join-Path $ProjectDir ".env"

Write-Host "📊 Trakt Discord Presence - Windows Status" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Check if task is installed
try {
    $Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $Task) {
        Write-Host "❌ Task not installed" -ForegroundColor Red
        Write-Host "   Run .\scripts\install.ps1 to install" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "✅ Task is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Task not installed" -ForegroundColor Red
    Write-Host "   Run .\scripts\install.ps1 to install" -ForegroundColor Yellow
    exit 1
}

# Check task status
$TaskInfo = Get-ScheduledTask -TaskName $TaskName
$TaskState = $TaskInfo.State
$LastResult = (Get-ScheduledTaskInfo -TaskName $TaskName).LastTaskResult
$LastRunTime = (Get-ScheduledTaskInfo -TaskName $TaskName).LastRunTime
$NextRunTime = (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime

switch ($TaskState) {
    "Ready" { 
        Write-Host "✅ Task is ready (not currently running)" -ForegroundColor Green
    }
    "Running" { 
        Write-Host "✅ Task is running" -ForegroundColor Green
        # Try to get process info
        try {
            $Processes = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*\.venv\Scripts\python.exe" }
            if ($Processes) {
                foreach ($Process in $Processes) {
                    Write-Host "   Process ID: $($Process.Id)" -ForegroundColor White
                }
            }
        } catch {
            # Ignore errors getting process info
        }
    }
    "Disabled" { 
        Write-Host "❌ Task is disabled" -ForegroundColor Red
        Write-Host "   Enable it with: Enable-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
    }
    default { 
        Write-Host "⚠️  Task state: $TaskState" -ForegroundColor Yellow
    }
}

if ($LastRunTime) {
    Write-Host "   Last run: $LastRunTime" -ForegroundColor White
}

if ($LastResult -ne $null) {
    if ($LastResult -eq 0) {
        Write-Host "   Last result: Success (0)" -ForegroundColor Green
    } else {
        Write-Host "   Last result: Error ($LastResult)" -ForegroundColor Red
    }
}

if ($NextRunTime) {
    Write-Host "   Next run: $NextRunTime" -ForegroundColor White
}

Write-Host ""

# Check configuration
if (Test-Path $EnvFile) {
    Write-Host "✅ Configuration file (.env) exists" -ForegroundColor Green
    
    # Check if required variables are set (without showing values)
    $EnvContent = Get-Content $EnvFile -Raw
    
    if ($EnvContent -match "TRAKT_CLIENT_ID=.+" -and ($EnvContent -match "TRAKT_CLIENT_ID=([^`r`n]+)" -and $Matches[1].Trim() -ne "")) {
        Write-Host "✅ TRAKT_CLIENT_ID is configured" -ForegroundColor Green
    } else {
        Write-Host "❌ TRAKT_CLIENT_ID is missing or empty" -ForegroundColor Red
    }
    
    if ($EnvContent -match "TRAKT_CLIENT_SECRET=.+" -and ($EnvContent -match "TRAKT_CLIENT_SECRET=([^`r`n]+)" -and $Matches[1].Trim() -ne "")) {
        Write-Host "✅ TRAKT_CLIENT_SECRET is configured" -ForegroundColor Green
    } else {
        Write-Host "❌ TRAKT_CLIENT_SECRET is missing or empty" -ForegroundColor Red
    }
    
    if ($EnvContent -match "DISCORD_CLIENT_ID=.+" -and ($EnvContent -match "DISCORD_CLIENT_ID=([^`r`n]+)" -and $Matches[1].Trim() -ne "")) {
        Write-Host "✅ DISCORD_CLIENT_ID is configured" -ForegroundColor Green
    } else {
        Write-Host "❌ DISCORD_CLIENT_ID is missing or empty" -ForegroundColor Red
    }
} else {
    Write-Host "❌ Configuration file (.env) missing" -ForegroundColor Red
    Write-Host "   Copy .env.example to .env and configure your API keys" -ForegroundColor Yellow
}

Write-Host ""

# Check virtual environment
$VenvDir = Join-Path $ProjectDir ".venv"
if (Test-Path $VenvDir) {
    Write-Host "✅ Python virtual environment exists" -ForegroundColor Green
} else {
    Write-Host "❌ Python virtual environment missing" -ForegroundColor Red
    Write-Host "   Run .\scripts\install.ps1 to create it" -ForegroundColor Yellow
}

Write-Host ""

# Show recent logs if they exist
$LogFile = Join-Path $LogsDir "trakt-discord.log"
$ErrorLogFile = Join-Path $LogsDir "trakt-discord-error.log"

if (Test-Path $LogFile) {
    Write-Host "📄 Recent activity log (last 10 lines):" -ForegroundColor Cyan
    Write-Host "----------------------------------------" -ForegroundColor Cyan
    try {
        $LogLines = Get-Content $LogFile -Tail 10 -ErrorAction SilentlyContinue
        if ($LogLines) {
            foreach ($Line in $LogLines) {
                Write-Host "   $Line" -ForegroundColor White
            }
        } else {
            Write-Host "   (Log file is empty)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "   (Could not read log file)" -ForegroundColor Gray
    }
    Write-Host ""
}

if ((Test-Path $ErrorLogFile) -and (Get-Item $ErrorLogFile).Length -gt 0) {
    Write-Host "⚠️  Recent error log (last 5 lines):" -ForegroundColor Yellow
    Write-Host "------------------------------------" -ForegroundColor Yellow
    try {
        $ErrorLines = Get-Content $ErrorLogFile -Tail 5 -ErrorAction SilentlyContinue
        if ($ErrorLines) {
            foreach ($Line in $ErrorLines) {
                Write-Host "   $Line" -ForegroundColor Red
            }
        }
    } catch {
        Write-Host "   (Could not read error log file)" -ForegroundColor Gray
    }
    Write-Host ""
}

Write-Host "🔍 For live logs, run:" -ForegroundColor Cyan
Write-Host "   Get-Content `"$LogFile`" -Tail 10 -Wait" -ForegroundColor White
Write-Host ""
Write-Host "⚙️  Task management:" -ForegroundColor Cyan
Write-Host "   • Restart: Restart-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
Write-Host "   • Stop:    Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
Write-Host "   • Start:   Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
Write-Host "   • GUI:     taskschd.msc (then find '$TaskName')" -ForegroundColor White