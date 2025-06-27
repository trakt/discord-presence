# Trakt Discord Presence - Windows Installation Script
# This script installs the Trakt Discord Presence app as a Windows Task Scheduler task

param(
    [switch]$Elevated
)

# Check if running as administrator (not required, but helpful for troubleshooting)
function Test-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Get script directory and project directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$LogsDir = Join-Path $ProjectDir "logs"
$VenvDir = Join-Path $ProjectDir ".venv"
$TaskName = "Trakt-Discord-Presence"

Write-Host "🎬 Trakt Discord Presence - Windows Installer" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

# Check if main.py exists
$MainPy = Join-Path $ProjectDir "main.py"
if (-not (Test-Path $MainPy)) {
    Write-Host "❌ Error: Could not find main.py in $ProjectDir" -ForegroundColor Red
    Write-Host "   Please make sure the project is in the correct location." -ForegroundColor Red
    exit 1
}

# Create logs directory
Write-Host "📁 Creating logs directory..." -ForegroundColor Yellow
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# Check for Python
$PythonCmd = $null
$PythonCommands = @("python", "python3", "py")

foreach ($cmd in $PythonCommands) {
    try {
        $version = & $cmd --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $version -match "Python 3\.\d+") {
            $PythonCmd = $cmd
            Write-Host "✅ Found Python: $version using '$cmd'" -ForegroundColor Green
            break
        }
    } catch {
        continue
    }
}

if (-not $PythonCmd) {
    Write-Host "❌ Error: Python 3.7+ not found!" -ForegroundColor Red
    Write-Host "   Please install Python from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "   Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists, create if not
if (-not (Test-Path $VenvDir)) {
    Write-Host "🐍 Creating Python virtual environment..." -ForegroundColor Yellow
    Set-Location $ProjectDir
    & $PythonCmd -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Virtual environment already exists" -ForegroundColor Green
    
    # Check if the virtual environment has correct paths (not from a different project)
    Write-Host "🔍 Validating virtual environment..." -ForegroundColor Yellow
    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    
    try {
        $null = & $VenvPython --version 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Invalid Python executable"
        }
        
        $null = & $VenvPython -m pip --version 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Invalid pip installation"
        }
        
        Write-Host "📦 Updating dependencies..." -ForegroundColor Yellow
        Set-Location $ProjectDir
        & $VenvPython -m pip install --upgrade pip
        & $VenvPython -m pip install -r requirements.txt
    } catch {
        Write-Host "⚠️  Virtual environment has invalid paths (likely copied from another project)" -ForegroundColor Yellow
        Write-Host "🗑️  Removing invalid virtual environment..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $VenvDir
        
        Write-Host "🐍 Creating new Python virtual environment..." -ForegroundColor Yellow
        Set-Location $ProjectDir
        & $PythonCmd -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
        $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
        & $VenvPython -m pip install --upgrade pip
        & $VenvPython -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
            exit 1
        }
    }
}

# Check if .env file exists
$EnvFile = Join-Path $ProjectDir ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "⚠️  Warning: .env file not found!" -ForegroundColor Yellow
    Write-Host "   Please copy .env.example to .env and configure your API keys:" -ForegroundColor Yellow
    Write-Host "   copy .env.example .env" -ForegroundColor Yellow
    Write-Host "   Then edit .env with your Trakt.tv and Discord credentials." -ForegroundColor Yellow
    Write-Host ""
}

# Remove existing task if it exists
Write-Host "🔄 Checking for existing task..." -ForegroundColor Yellow
try {
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "   Removing existing task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
} catch {
    # Task doesn't exist, which is fine
}

# Create the scheduled task
Write-Host "🚀 Creating scheduled task..." -ForegroundColor Yellow

$VenvPythonPath = Join-Path $VenvDir "Scripts\python.exe"
$MainPyPath = Join-Path $ProjectDir "main.py"
$LogPath = Join-Path $LogsDir "trakt-discord.log"
$ErrorLogPath = Join-Path $LogsDir "trakt-discord-error.log"

# Create task action
$Action = New-ScheduledTaskAction -Execute $VenvPythonPath -Argument "`"$MainPyPath`"" -WorkingDirectory $ProjectDir

# Create task trigger (at logon)
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Create task settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 0)

# Create task principal (run as current user)
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

# Register the task
try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Trakt Discord Presence - Shows your Trakt.tv activity in Discord" | Out-Null
    
    # Start the task immediately
    Start-ScheduledTask -TaskName $TaskName
    
    Write-Host "✅ Task created and started successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create scheduled task: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Give it a moment to start
Start-Sleep -Seconds 3

# Check if task is running
$TaskInfo = Get-ScheduledTask -TaskName $TaskName
$TaskState = (Get-ScheduledTask -TaskName $TaskName).State

Write-Host ""
Write-Host "📋 Installation Summary:" -ForegroundColor Green
Write-Host "   • Task Name: $TaskName" -ForegroundColor White
Write-Host "   • Status: $TaskState" -ForegroundColor White
Write-Host "   • Python: $VenvPythonPath" -ForegroundColor White
Write-Host "   • Script: $MainPyPath" -ForegroundColor White
Write-Host "   • Logs: $LogsDir" -ForegroundColor White
Write-Host "   • Auto-start: Enabled (starts at user login)" -ForegroundColor White
Write-Host ""
Write-Host "🔍 To check logs:" -ForegroundColor Cyan
Write-Host "   Get-Content `"$LogPath`" -Tail 10 -Wait" -ForegroundColor White
Write-Host ""
Write-Host "⚙️  To manage the task:" -ForegroundColor Cyan
Write-Host "   • Status:  .\scripts\status.ps1" -ForegroundColor White
Write-Host "   • Stop:    Stop-ScheduledTask -TaskName `"$TaskName`"" -ForegroundColor White
Write-Host "   • Start:   Start-ScheduledTask -TaskName `"$TaskName`"" -ForegroundColor White
Write-Host "   • Restart: Restart-ScheduledTask -TaskName `"$TaskName`"" -ForegroundColor White
Write-Host ""
Write-Host "🗑️  To uninstall:" -ForegroundColor Cyan
Write-Host "   .\scripts\uninstall.ps1" -ForegroundColor White
Write-Host ""

if (-not (Test-Path $EnvFile)) {
    Write-Host "⚠️  Don't forget to configure your .env file before the service will work!" -ForegroundColor Yellow
} else {
    Write-Host "🎉 Setup complete! The task will now run automatically." -ForegroundColor Green
    Write-Host "   Make sure Discord is running and check-in to something on Trakt.tv!" -ForegroundColor Green
}

Write-Host ""
Write-Host "💡 Tip: You can also manage the task through Task Scheduler GUI:" -ForegroundColor Cyan
Write-Host "   Press Win+R, type 'taskschd.msc', find '$TaskName'" -ForegroundColor White