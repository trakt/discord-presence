#!/bin/bash

# Trakt Discord Presence - macOS Daemon Uninstaller
# This script removes the Trakt Discord Presence LaunchAgent daemon

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PLIST_NAME="com.user.trakt-discord-presence.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "🗑️  Trakt Discord Presence - macOS Daemon Uninstaller"
echo "===================================================="
echo

# Check if the plist file exists
if [ ! -f "$LAUNCH_AGENTS_DIR/$PLIST_NAME" ]; then
    echo "ℹ️  Service not found. Nothing to uninstall."
    exit 0
fi

# Stop and unload the service
echo "⏹️  Stopping service..."
launchctl unload "$LAUNCH_AGENTS_DIR/$PLIST_NAME" 2>/dev/null || echo "   (Service was not running)"

# Remove the plist file
echo "🗂️  Removing LaunchAgent file..."
rm -f "$LAUNCH_AGENTS_DIR/$PLIST_NAME"

# Check if service is still listed
if launchctl list | grep -q "com.user.trakt-discord-presence"; then
    echo "⚠️  Service may still be running. Try logging out and back in."
else
    echo "✅ Service successfully uninstalled!"
fi

echo
echo "📁 Project files remain at: $PROJECT_DIR"
echo "   • Python code and configuration are untouched"
echo "   • Virtual environment (.venv) is preserved"  
echo "   • Log files are preserved in logs/ directory"
echo
echo "🔄 To reinstall the daemon, run: ./install-daemon.sh"
echo
echo "🗑️  To completely remove the project:"
echo "   rm -rf \"$PROJECT_DIR\""