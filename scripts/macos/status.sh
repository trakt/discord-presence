#!/bin/bash

# Trakt Discord Presence - Status Checker
# This script checks the status of the daemon and shows recent logs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PLIST_NAME="com.user.trakt-discord-presence.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
LOGS_DIR="$PROJECT_DIR/logs"

echo "📊 Trakt Discord Presence - Status Check"
echo "========================================"
echo

# Check if daemon is installed
if [ ! -f "$LAUNCH_AGENTS_DIR/$PLIST_NAME" ]; then
    echo "❌ Daemon not installed"
    echo "   Run ./install-daemon.sh to install"
    exit 1
fi

echo "✅ Daemon is installed"

# Check if daemon is loaded/running
if launchctl list | grep -q "com.user.trakt-discord-presence"; then
    echo "✅ Daemon is running"
    
    # Get PID if available
    PID=$(launchctl list | grep "com.user.trakt-discord-presence" | awk '{print $1}')
    if [ "$PID" != "-" ]; then
        echo "   Process ID: $PID"
    fi
else
    echo "❌ Daemon is not running"
    echo "   Try: launchctl load ~/Library/LaunchAgents/$PLIST_NAME"
fi

echo

# Check configuration
if [ -f "$PROJECT_DIR/.env" ]; then
    echo "✅ Configuration file (.env) exists"
    
    # Check if required variables are set (without showing values)
    if grep -q "TRAKT_CLIENT_ID=" "$PROJECT_DIR/.env" && [ -n "$(grep "TRAKT_CLIENT_ID=" "$PROJECT_DIR/.env" | cut -d'=' -f2)" ]; then
        echo "✅ TRAKT_CLIENT_ID is configured"
    else
        echo "❌ TRAKT_CLIENT_ID is missing or empty"
    fi
    
    if grep -q "TRAKT_CLIENT_SECRET=" "$PROJECT_DIR/.env" && [ -n "$(grep "TRAKT_CLIENT_SECRET=" "$PROJECT_DIR/.env" | cut -d'=' -f2)" ]; then
        echo "✅ TRAKT_CLIENT_SECRET is configured"
    else
        echo "❌ TRAKT_CLIENT_SECRET is missing or empty"
    fi
    
    if grep -q "DISCORD_CLIENT_ID=" "$PROJECT_DIR/.env" && [ -n "$(grep "DISCORD_CLIENT_ID=" "$PROJECT_DIR/.env" | cut -d'=' -f2)" ]; then
        echo "✅ DISCORD_CLIENT_ID is configured"
    else
        echo "❌ DISCORD_CLIENT_ID is missing or empty"
    fi
else
    echo "❌ Configuration file (.env) missing"
    echo "   Copy .env.example to .env and configure your API keys"
fi

echo

# Check virtual environment
if [ -d "$PROJECT_DIR/.venv" ]; then
    echo "✅ Python virtual environment exists"
else
    echo "❌ Python virtual environment missing"
    echo "   Run ./install-daemon.sh to create it"
fi

echo

# Show recent logs if they exist
if [ -f "$LOGS_DIR/trakt-discord.log" ]; then
    echo "📄 Recent activity log (last 10 lines):"
    echo "----------------------------------------"
    tail -n 10 "$LOGS_DIR/trakt-discord.log" | sed 's/^/   /'
    echo
fi

if [ -f "$LOGS_DIR/trakt-discord-error.log" ] && [ -s "$LOGS_DIR/trakt-discord-error.log" ]; then
    echo "⚠️  Recent error log (last 5 lines):"
    echo "------------------------------------"
    tail -n 5 "$LOGS_DIR/trakt-discord-error.log" | sed 's/^/   /'
    echo
fi

echo "🔍 For live logs, run:"
echo "   tail -f $LOGS_DIR/trakt-discord.log"
echo
echo "⚙️  Daemon management:"
echo "   • Restart: launchctl unload ~/Library/LaunchAgents/$PLIST_NAME && launchctl load ~/Library/LaunchAgents/$PLIST_NAME"
echo "   • Stop:    launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
echo "   • Start:   launchctl load ~/Library/LaunchAgents/$PLIST_NAME"