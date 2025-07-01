#!/usr/bin/env python3
"""
Cross-platform daemon installer for Trakt Discord Presence.
Automatically detects the platform and uses the appropriate method.
"""

import os
import sys
import platform
import subprocess
import argparse
from pathlib import Path

def get_platform():
    """Detect the current platform."""
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    elif system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    else:
        return "unknown"

def check_prerequisites():
    """Check basic prerequisites."""
    project_dir = Path(__file__).parent
    env_file = project_dir / ".env"
    
    if not env_file.exists():
        print("❌ Error: .env file not found!")
        print("Please copy .env.example to .env and configure your credentials:")
        print("  cp .env.example .env")
        print("  # Edit .env with your Trakt and Discord credentials")
        return False
    
    # Check if required environment variables are set
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ["TRAKT_CLIENT_ID", "TRAKT_CLIENT_SECRET", "TRAKT_APPLICATION_ID", "DISCORD_CLIENT_ID"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Error: Missing required environment variables in .env:")
        for var in missing_vars:
            print(f"  {var}")
        print("\nPlease edit your .env file and add these credentials.")
        return False
    
    return True

def install_linux():
    """Install using systemd on Linux."""
    try:
        from daemon_manager import SystemdInstaller
        installer = SystemdInstaller()
        installer.install()
        return True
    except ImportError:
        print("❌ Error: daemon_manager.py not found")
        return False
    except Exception as e:
        print(f"❌ Error installing on Linux: {e}")
        return False

def install_macos():
    """Install using launchd on macOS."""
    print("🍎 macOS detected")
    print("⚠️  macOS daemon installation not yet implemented.")
    print("For now, you can run manually:")
    print("  python main.py")
    print("\nTo run automatically on startup:")
    print("1. Add to your shell profile (.bashrc, .zshrc):")
    print("   cd /path/to/discord-presence && python main.py --daemon &")
    print("2. Or use a tool like 'brew install launchctl-completion'")
    return False

def install_windows():
    """Install using Task Scheduler on Windows."""
    print("🪟 Windows detected")
    print("⚠️  Windows daemon installation not yet implemented.")
    print("For now, you can run manually:")
    print("  python main.py")
    print("\nTo run automatically on startup:")
    print("1. Add to Windows startup folder:")
    print("   Win+R → shell:startup")
    print("2. Create a batch file that runs: python main.py --daemon")
    return False

def uninstall_linux():
    """Uninstall systemd service on Linux."""
    try:
        from daemon_manager import SystemdInstaller
        installer = SystemdInstaller()
        installer.uninstall()
        return True
    except Exception as e:
        print(f"❌ Error uninstalling on Linux: {e}")
        return False

def show_status():
    """Show current daemon status."""
    current_platform = get_platform()
    
    if current_platform == "linux":
        try:
            from daemon_manager import SystemdInstaller
            installer = SystemdInstaller()
            
            if installer.is_installed():
                print("✅ Daemon is installed")
                if installer.is_running():
                    print("🟢 Daemon is running")
                else:
                    print("🔴 Daemon is stopped")
                    print("Start it with: python install.py start")
            else:
                print("❌ Daemon is not installed")
                print("Install it with: python install.py install")
        except Exception as e:
            print(f"❌ Error checking status: {e}")
    else:
        print(f"📊 Platform: {current_platform}")
        print("⚠️  Daemon not supported on this platform yet")

def main():
    parser = argparse.ArgumentParser(description="Trakt Discord Presence Installer")
    parser.add_argument("action", choices=[
        "install", "uninstall", "status", "start", "stop", "logs", "test"
    ], help="Action to perform")
    
    args = parser.parse_args()
    current_platform = get_platform()
    
    print(f"🎬 Trakt Discord Presence Installer")
    print(f"📊 Platform: {current_platform}")
    print()
    
    if args.action == "test":
        print("🧪 Testing configuration...")
        if check_prerequisites():
            print("✅ Prerequisites check passed!")
            print("You can now run: python main.py")
        return
    
    if args.action == "status":
        show_status()
        return
    
    if args.action == "install":
        if not check_prerequisites():
            return
        
        if current_platform == "linux":
            if install_linux():
                print("🎉 Installation completed!")
            else:
                sys.exit(1)
        elif current_platform == "macos":
            install_macos()
        elif current_platform == "windows":
            install_windows()
        else:
            print(f"❌ Unsupported platform: {current_platform}")
            sys.exit(1)
    
    elif args.action == "uninstall":
        if current_platform == "linux":
            if uninstall_linux():
                print("✅ Uninstallation completed!")
        else:
            print(f"⚠️  Uninstall not implemented for {current_platform}")
    
    elif args.action in ["start", "stop", "logs"]:
        if current_platform == "linux":
            try:
                from daemon_manager import SystemdInstaller
                installer = SystemdInstaller()
                
                if args.action == "start":
                    installer.start()
                elif args.action == "stop":
                    installer.stop()
                elif args.action == "logs":
                    installer.logs(follow=True)
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print(f"⚠️  Daemon control not implemented for {current_platform}")

if __name__ == "__main__":
    main()
