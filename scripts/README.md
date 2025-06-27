# Cross-Platform Daemon Scripts

Installation scripts for running Trakt Discord Presence as a background daemon/service.

## 🚀 Quick Start

```bash
# From the project root directory:
./scripts/install.sh    # Install daemon (auto-detects OS)
./scripts/status.sh     # Check daemon status and logs
./scripts/uninstall.sh  # Uninstall daemon (preserves project)
```

## 🗂️ Structure

```
scripts/
├── install.sh          # Universal installer (detects OS)
├── status.sh           # Universal status checker
├── uninstall.sh        # Universal uninstaller  
├── macos/              # macOS LaunchAgent scripts
├── windows/            # Windows Task Scheduler scripts
└── linux/              # Linux systemd scripts (planned)
```

## 🖥️ Platform Support

| Platform | Status | Implementation | Auto-Start |
|----------|--------|----------------|------------|
| **macOS** | ✅ Complete | LaunchAgents | On login |
| **Windows** | ✅ Complete | Task Scheduler + PowerShell | On login |
| **Linux** | 🚧 Planned | systemd user services | On login |

## 📋 How It Works

The universal scripts detect your OS and run the appropriate platform-specific installer:

```bash
# Detects OS using uname -s:
Darwin* → macos/
Linux* → linux/
CYGWIN*|MINGW*|MSYS* → windows/
```

Each platform directory contains install/uninstall/status scripts plus platform-specific documentation.

## 🤝 Contributing

To add a new platform:
1. Create `scripts/[platform]/` directory
2. Add `install.sh`, `uninstall.sh`, `status.sh` scripts
3. Update OS detection in universal scripts
4. Add platform documentation

See existing implementations as reference:
- [macOS Implementation](macos/README.md)
- [Windows Implementation](windows/README.md)