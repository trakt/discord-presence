#!/bin/bash

# Trakt Discord Presence - Cross-Platform Uninstaller
# Automatically detects your operating system and runs the appropriate uninstaller

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🗑️  Trakt Discord Presence - Cross-Platform Uninstaller"
echo "======================================================="
echo

# Detect operating system
case "$(uname -s)" in
    Darwin*)
        PLATFORM="macos"
        ;;
    Linux*)
        PLATFORM="linux"
        ;;
    CYGWIN*|MINGW32*|MINGW64*|MSYS*)
        PLATFORM="windows"
        ;;
    *)
        echo "❌ Unknown operating system: $(uname -s)"
        exit 1
        ;;
esac

PLATFORM_SCRIPT_DIR="$SCRIPT_DIR/$PLATFORM"

# Check if platform-specific uninstaller exists
if [ "$PLATFORM" = "windows" ]; then
    UNINSTALL_SCRIPT="$PLATFORM_SCRIPT_DIR/uninstall.ps1"
    if [ ! -f "$UNINSTALL_SCRIPT" ]; then
        echo "❌ Uninstaller not found for $PLATFORM"
        echo "   Expected: $UNINSTALL_SCRIPT"
        exit 1
    fi
else
    UNINSTALL_SCRIPT="$PLATFORM_SCRIPT_DIR/uninstall.sh"
    if [ ! -f "$UNINSTALL_SCRIPT" ]; then
        echo "❌ Uninstaller not found for $PLATFORM"
        echo "   Expected: $UNINSTALL_SCRIPT"
        exit 1
    fi
    # Make sure the platform uninstaller is executable
    chmod +x "$UNINSTALL_SCRIPT"
fi

# Run the platform-specific uninstaller
cd "$PROJECT_DIR"

if [ "$PLATFORM" = "windows" ]; then
    # For Windows, run PowerShell script
    if command -v powershell.exe >/dev/null 2>&1; then
        powershell.exe -ExecutionPolicy Bypass -File "$UNINSTALL_SCRIPT"
    elif command -v pwsh >/dev/null 2>&1; then
        pwsh -ExecutionPolicy Bypass -File "$UNINSTALL_SCRIPT"
    else
        echo "❌ PowerShell not found. Please install PowerShell or use the .bat files:"
        echo "   $PLATFORM_SCRIPT_DIR/uninstall.bat"
        exit 1
    fi
else
    # For Unix-like systems, run shell script
    exec "$UNINSTALL_SCRIPT"
fi