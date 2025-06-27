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
if [ ! -f "$PLATFORM_SCRIPT_DIR/uninstall.sh" ]; then
    echo "❌ Uninstaller not found for $PLATFORM"
    echo "   Expected: $PLATFORM_SCRIPT_DIR/uninstall.sh"
    exit 1
fi

# Make sure the platform uninstaller is executable
chmod +x "$PLATFORM_SCRIPT_DIR/uninstall.sh"

# Run the platform-specific uninstaller
cd "$PROJECT_DIR"
exec "$PLATFORM_SCRIPT_DIR/uninstall.sh"