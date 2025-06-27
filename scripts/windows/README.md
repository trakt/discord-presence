# Windows Task Scheduler Installation

Windows support using Task Scheduler and PowerShell scripts.

## 🚀 Usage:

### Cross-Platform (Recommended)
```bash
./scripts/install.sh    # Auto-detects Windows
./scripts/status.sh     # Check status and logs
./scripts/uninstall.sh  # Remove daemon
```

### Windows-Specific Options
```powershell
# PowerShell:
.\scripts\windows\install.ps1
.\scripts\windows\status.ps1
.\scripts\windows\uninstall.ps1

# Double-click in File Explorer:
scripts\windows\install.bat
scripts\windows\status.bat
scripts\windows\uninstall.bat
```

## 📁 Files:
- `install.ps1` / `install.bat` - Installs scheduled task
- `uninstall.ps1` / `uninstall.bat` - Removes scheduled task  
- `status.ps1` / `status.bat` - Shows task status and logs

## ⚙️ How it works:
- Creates Windows scheduled task "Trakt-Discord-Presence"
- Runs at user logon (no admin required)
- Uses project's Python virtual environment
- Auto-restarts if app crashes
- Logs to `logs/` directory

## 🛠️ Requirements:
- Windows 10+ with PowerShell 5.0+
- Python 3.7+ in PATH
- Discord Desktop app

## 🔧 Manual task control:
```powershell
Start-ScheduledTask -TaskName "Trakt-Discord-Presence"
Stop-ScheduledTask -TaskName "Trakt-Discord-Presence"
# Or use Task Scheduler GUI: Win+R → taskschd.msc
```
