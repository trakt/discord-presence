# Windows Service Installation

This directory will contain scripts for installing Trakt Discord Presence as a Windows service.

## Planned Implementation:
- Windows Task Scheduler integration
- PowerShell installation scripts
- Windows Service wrapper (optional)
- Auto-start on user login
- System tray integration (optional)

## Planned Files:
- `install.ps1` - PowerShell installer script
- `uninstall.ps1` - PowerShell uninstaller script  
- `status.ps1` - Status checker script
- `install.bat` - Batch file wrapper for install.ps1
- `task-scheduler.xml` - Task Scheduler template

## Usage (when implemented):
```bash
# From project root (Git Bash/PowerShell):
./scripts/install.sh    # Cross-platform installer (auto-detects Windows)
./scripts/status.sh     # Cross-platform status checker  
./scripts/uninstall.sh  # Cross-platform uninstaller

# Or run Windows-specific scripts:
./scripts/windows/install.ps1
./scripts/windows/status.ps1
./scripts/windows/uninstall.ps1
```

## Contribution Welcome:
If you'd like to implement Windows support, please see the macOS implementation as a reference and submit a pull request!
