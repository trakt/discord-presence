#!/bin/bash

# Trakt Discord Presence - Cross-Platform Daemon Installer
# Automatically detects your operating system and runs the appropriate installer

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🎬 Trakt Discord Presence - Cross-Platform Installer"
echo "===================================================="
echo

# Detect operating system
case "$(uname -s)" in
    Darwin*)
        echo "🍎 Detected macOS"
        PLATFORM="macos"
        ;;
    Linux*)
        echo "🐧 Detected Linux"
        PLATFORM="linux"
        ;;
    CYGWIN*|MINGW32*|MINGW64*|MSYS*)
        echo "🪟 Detected Windows (Git Bash/MSYS)"
        PLATFORM="windows"
        ;;
    *)
        echo "❌ Unknown operating system: $(uname -s)"
        echo "   Supported platforms: macOS, Linux, Windows"
        exit 1
        ;;
esac

PLATFORM_SCRIPT_DIR="$SCRIPT_DIR/$PLATFORM"

# Check if platform-specific installer exists
if [ ! -d "$PLATFORM_SCRIPT_DIR" ]; then
    echo "❌ Platform support not implemented yet: $PLATFORM"
    echo "   Available platforms:"
    for dir in "$SCRIPT_DIR"/*/; do
        if [ -d "$dir" ]; then
            basename "$dir"
        fi
    done
    exit 1
fi

if [ ! -f "$PLATFORM_SCRIPT_DIR/install.sh" ]; then
    echo "❌ Installer not found for $PLATFORM"
    echo "   Expected: $PLATFORM_SCRIPT_DIR/install.sh"
    exit 1
fi

# Make sure the platform installer is executable
chmod +x "$PLATFORM_SCRIPT_DIR/install.sh"

# Run the platform-specific installer
echo "🚀 Running $PLATFORM installer..."
echo
cd "$PROJECT_DIR"
exec "$PLATFORM_SCRIPT_DIR/install.sh"