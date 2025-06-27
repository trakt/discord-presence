# macOS Daemon Installation

This directory contains scripts for installing Trakt Discord Presence as a macOS daemon using LaunchAgents.

## Files:
- `install.sh` - Installs the daemon and sets up auto-start on login
- `uninstall.sh` - Removes the daemon (preserves project files)  
- `status.sh` - Checks daemon status and shows logs
- `README.md` - This documentation file

Note: The LaunchAgent plist file is dynamically generated during installation with the correct paths.

## Usage:
```bash
# From project root directory:
./scripts/install.sh    # Cross-platform installer (auto-detects macOS)
./scripts/status.sh     # Cross-platform status checker
./scripts/uninstall.sh  # Cross-platform uninstaller

# Or run macOS-specific scripts directly:
./scripts/macos/install.sh
./scripts/macos/status.sh  
./scripts/macos/uninstall.sh
```

## How it works:
- Uses macOS LaunchAgents for proper user-level daemon management
- Automatically starts on user login
- Restarts if the application crashes
- Logs to `logs/` directory in project root
- Runs in background without terminal window
