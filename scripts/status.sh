#!/bin/bash

# Trakt Discord Presence - Cross-Platform Status Checker
# Automatically detects your operating system and runs the appropriate status checker

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "📊 Trakt Discord Presence - Cross-Platform Status"
echo "================================================"
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

# Check if platform-specific status checker exists
if [ "$PLATFORM" = "windows" ]; then
    STATUS_SCRIPT="$PLATFORM_SCRIPT_DIR/status.ps1"
    if [ ! -f "$STATUS_SCRIPT" ]; then
        echo "❌ Status checker not found for $PLATFORM"
        echo "   Expected: $STATUS_SCRIPT"
        exit 1
    fi
else
    STATUS_SCRIPT="$PLATFORM_SCRIPT_DIR/status.sh"
    if [ ! -f "$STATUS_SCRIPT" ]; then
        echo "❌ Status checker not found for $PLATFORM"
        echo "   Expected: $STATUS_SCRIPT"
        exit 1
    fi
    # Make sure the platform status checker is executable
    chmod +x "$STATUS_SCRIPT"
fi

# Run the platform-specific status checker
cd "$PROJECT_DIR"

if [ "$PLATFORM" = "windows" ]; then
    # For Windows, run PowerShell script
    if command -v powershell.exe >/dev/null 2>&1; then
        powershell.exe -ExecutionPolicy Bypass -File "$STATUS_SCRIPT"
    elif command -v pwsh >/dev/null 2>&1; then
        pwsh -ExecutionPolicy Bypass -File "$STATUS_SCRIPT"
    else
        echo "❌ PowerShell not found. Please install PowerShell or use the .bat files:"
        echo "   $PLATFORM_SCRIPT_DIR/status.bat"
        exit 1
    fi
else
    # For Unix-like systems, run shell script
    exec "$STATUS_SCRIPT"
fi