#!/bin/bash

# Trakt Discord Presence - macOS Daemon Installer
# This script installs the Trakt Discord Presence app as a LaunchAgent daemon

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PLIST_NAME="com.user.trakt-discord-presence.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
LOGS_DIR="$PROJECT_DIR/logs"

echo "🎬 Trakt Discord Presence - macOS Daemon Installer"
echo "=================================================="
echo

# Check if we're in the right directory
if [ ! -f "$PROJECT_DIR/main.py" ]; then
    echo "❌ Error: Could not find main.py in $PROJECT_DIR"
    echo "   Please make sure the project is in the correct location."
    exit 1
fi

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p "$LOGS_DIR"

# Check if virtual environment exists, create if not
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    cd "$PROJECT_DIR"
    python3 -m venv .venv
    
    echo "📦 Installing dependencies..."
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
else
    echo "✅ Virtual environment already exists"
    
    # Check if the virtual environment has correct paths (not from a different project)
    echo "🔍 Validating virtual environment..."
    if ! .venv/bin/python --version >/dev/null 2>&1 || ! .venv/bin/pip --version >/dev/null 2>&1; then
        echo "⚠️  Virtual environment has invalid paths (likely copied from another project)"
        echo "🗑️  Removing invalid virtual environment..."
        rm -rf .venv
        
        echo "🐍 Creating new Python virtual environment..."
        cd "$PROJECT_DIR"
        python3 -m venv .venv
        
        echo "📦 Installing dependencies..."
        .venv/bin/pip install --upgrade pip
        .venv/bin/pip install -r requirements.txt
    else
        echo "📦 Updating dependencies..."
        cd "$PROJECT_DIR"
        .venv/bin/pip install --upgrade pip
        .venv/bin/pip install -r requirements.txt
    fi
fi

# Check if .env file exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Please copy .env.example to .env and configure your API keys:"
    echo "   cp .env.example .env"
    echo "   Then edit .env with your Trakt.tv and Discord credentials."
    echo
fi

# Create LaunchAgents directory if it doesn't exist
echo "📂 Setting up LaunchAgent..."
mkdir -p "$LAUNCH_AGENTS_DIR"

# Generate plist file with correct paths
echo "📝 Generating LaunchAgent configuration..."
cat > "$LAUNCH_AGENTS_DIR/$PLIST_NAME" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.trakt-discord-presence</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/.venv/bin/python</string>
        <string>$PROJECT_DIR/main.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>$LOGS_DIR/trakt-discord.log</string>
    
    <key>StandardErrorPath</key>
    <string>$LOGS_DIR/trakt-discord-error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    
    <key>ThrottleInterval</key>
    <integer>10</integer>
    
    <key>StartInterval</key>
    <integer>30</integer>
</dict>
</plist>
EOF

# Unload existing service if it's already loaded (ignore errors)
echo "🔄 Stopping existing service (if running)..."
launchctl unload "$LAUNCH_AGENTS_DIR/$PLIST_NAME" 2>/dev/null || true

# Load the LaunchAgent
echo "🚀 Loading LaunchAgent..."
launchctl load "$LAUNCH_AGENTS_DIR/$PLIST_NAME"

# Give it a moment to start
sleep 2

# Check if the service is running
if launchctl list | grep -q "com.user.trakt-discord-presence"; then
    echo "✅ Service installed and started successfully!"
    echo
    echo "📋 Service Status:"
    echo "   • Name: com.user.trakt-discord-presence"
    echo "   • Location: $LAUNCH_AGENTS_DIR/$PLIST_NAME"
    echo "   • Logs: $LOGS_DIR/"
    echo "   • Auto-start: Enabled (starts on login)"
    echo
    echo "🔍 To check logs:"
    echo "   tail -f $LOGS_DIR/trakt-discord.log"
    echo "   tail -f $LOGS_DIR/trakt-discord-error.log"
    echo
    echo "⚙️  To manage the service:"
    echo "   • Stop:    launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
    echo "   • Start:   launchctl load ~/Library/LaunchAgents/$PLIST_NAME"
    echo "   • Restart: launchctl unload ~/Library/LaunchAgents/$PLIST_NAME && launchctl load ~/Library/LaunchAgents/$PLIST_NAME"
    echo
    echo "🗑️  To uninstall:"
    echo "   Run: ./uninstall-daemon.sh"
    echo
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        echo "⚠️  Don't forget to configure your .env file before the service will work!"
    else
        echo "🎉 Setup complete! The service will now run automatically."
        echo "   Make sure Discord is running and check-in to something on Trakt.tv!"
    fi
else
    echo "❌ Failed to start service. Check the logs for details:"
    echo "   $LOGS_DIR/trakt-discord-error.log"
    exit 1
fi