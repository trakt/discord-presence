# Cross-Platform Daemon Scripts

This directory contains installation scripts for running Trakt Discord Presence as a background daemon/service on different operating systems.

## 🚀 Quick Start

The universal scripts automatically detect your operating system and run the appropriate platform-specific installer:

```bash
# From the project root directory:
./scripts/install.sh    # Install daemon (auto-detects OS)
./scripts/status.sh     # Check daemon status and logs
./scripts/uninstall.sh  # Uninstall daemon (preserves project)
```

## 🗂️ Directory Structure

```
scripts/
├── install.sh          # Universal installer (detects OS)
├── status.sh           # Universal status checker
├── uninstall.sh        # Universal uninstaller  
├── macos/              # macOS LaunchAgent scripts
├── windows/            # Windows Task Scheduler scripts (coming soon)
└── linux/              # Linux systemd scripts (coming soon)
```

## 🖥️ Platform Support

| Platform | Status | Implementation | Auto-Start | Logs |
|----------|--------|----------------|------------|------|
| **macOS** | ✅ Complete | LaunchAgents | On login | `logs/` directory |
| **Windows** | 🚧 Planned | Task Scheduler + PowerShell | On login | Event Log + files |
| **Linux** | 🚧 Planned | systemd user services | On login | journalctl + files |

## 📋 How It Works

### Universal Scripts
The universal scripts (`install.sh`, `status.sh`, `uninstall.sh`) detect your operating system using `uname -s` and then execute the appropriate platform-specific script.

### Platform-Specific Scripts
Each platform directory contains:
- `install.sh` - Installs the daemon/service
- `uninstall.sh` - Removes the daemon/service  
- `status.sh` - Checks status and shows logs
- Platform-specific configuration files
- `README.md` - Platform-specific documentation

## 🛠️ Development

### Adding a New Platform

1. Create a new directory: `scripts/[platform]/`
2. Add the three required scripts: `install.sh`, `uninstall.sh`, `status.sh`
3. Make scripts executable: `chmod +x scripts/[platform]/*.sh`
4. Add platform detection to the universal scripts
5. Test thoroughly on the target platform
6. Update documentation

### Platform Detection
The universal scripts use this logic:
```bash
case "$(uname -s)" in
    Darwin*)  PLATFORM="macos" ;;
    Linux*)   PLATFORM="linux" ;;
    CYGWIN*|MINGW*|MSYS*) PLATFORM="windows" ;;
esac
```

## 🤝 Contributing

Contributions for Windows and Linux support are welcome! Please:

1. Follow the existing macOS implementation as a reference
2. Ensure scripts work without requiring root/admin privileges when possible
3. Use the platform's standard service management system
4. Include proper error handling and logging
5. Test on multiple versions of the target OS
6. Update this README with your changes

## 📚 Platform Documentation

- [macOS Implementation](macos/README.md) - LaunchAgents setup
- [Windows Implementation](windows/README.md) - Planned Task Scheduler setup  
- [Linux Implementation](linux/README.md) - Planned systemd setup