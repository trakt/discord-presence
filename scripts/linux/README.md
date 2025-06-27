# Linux Systemd Service Installation

This directory will contain scripts for installing Trakt Discord Presence as a Linux systemd user service.

## Planned Implementation:
- Systemd user service (not system-wide)
- Auto-start on user login
- Proper dependency management
- Service logs via journalctl
- Support for major Linux distributions

## Planned Files:
- `install.sh` - Bash installer script
- `uninstall.sh` - Bash uninstaller script
- `status.sh` - Status checker script  
- `trakt-discord-presence.service` - Systemd service template

## Usage (when implemented):
```bash
# From project root:
./scripts/install.sh    # Cross-platform installer (auto-detects Linux)
./scripts/status.sh     # Cross-platform status checker
./scripts/uninstall.sh  # Cross-platform uninstaller

# Or run Linux-specific scripts:
./scripts/linux/install.sh
./scripts/linux/status.sh
./scripts/linux/uninstall.sh
```

## How it will work:
- Uses systemd user services (--user flag)
- Installs to `~/.config/systemd/user/`
- Enables auto-start with `systemctl --user enable`
- Logs accessible via `journalctl --user -u trakt-discord-presence`
- No root privileges required

## Contribution Welcome:
If you'd like to implement Linux support, please see the macOS implementation as a reference and submit a pull request!
