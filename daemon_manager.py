#!/usr/bin/env python3
"""
Cross-platform daemon installer and manager for Trakt Discord Presence.
Supports Linux (systemd) and macOS (launchd).
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse
import platform
import textwrap

class SystemdInstaller:
    def __init__(self):
        self.app_name = "trakt-discord-presence"
        self.service_name = f"{self.app_name}.service"
        self.user_service_dir = Path.home() / ".config" / "systemd" / "user"
        self.project_dir = Path(__file__).parent.absolute()
        self.venv_dir = self.project_dir / ".venv"
        self.main_script = self.project_dir / "main.py"
        
    def check_requirements(self):
        """Check if systemd and required files exist."""
        if not shutil.which("systemctl"):
            raise RuntimeError("systemctl not found. This system doesn't support systemd.")
        
        if not self.main_script.exists():
            raise RuntimeError(f"main.py not found in {self.project_dir}")
        
        if not (self.project_dir / ".env").exists():
            raise RuntimeError(".env file not found. Please configure your credentials first.")
    
    def setup_venv(self):
        """Ensure virtual environment exists and has dependencies."""
        if not self.venv_dir.exists():
            print("Creating virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", str(self.venv_dir)], check=True)
        
        # Install dependencies
        pip_path = self.venv_dir / "bin" / "pip"
        requirements_file = self.project_dir / "requirements.txt"
        
        if requirements_file.exists():
            print("Installing dependencies...")
            subprocess.run([str(pip_path), "install", "-r", str(requirements_file)], check=True)
    
    def create_service_file(self):
        """Create systemd service file."""
        python_path = self.venv_dir / "bin" / "python"
        
        service_content = f"""[Unit]
Description=Trakt Discord Presence Bot
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart={python_path} {self.main_script}
WorkingDirectory={self.project_dir}
Restart=always
RestartSec=10
Environment=DISPLAY=:0

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier={self.app_name}

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths={self.project_dir}

[Install]
WantedBy=default.target
"""
        
        # Create user systemd directory if it doesn't exist
        self.user_service_dir.mkdir(parents=True, exist_ok=True)
        
        # Write service file
        service_file = self.user_service_dir / self.service_name
        service_file.write_text(service_content)
        
        print(f"Created service file: {service_file}")
        return service_file
    
    def install(self):
        """Install and enable the systemd service."""
        print("Installing Trakt Discord Presence daemon...")
        
        self.check_requirements()
        self.setup_venv()
        self.create_service_file()
        
        # Reload systemd user daemon
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        
        # Enable service
        subprocess.run(["systemctl", "--user", "enable", self.service_name], check=True)
        
        print(f"✅ Service installed and enabled!")
        print(f"The bot will start automatically on next login.")
        print(f"\nManagement commands:")
        print(f"  Start:   systemctl --user start {self.service_name}")
        print(f"  Stop:    systemctl --user stop {self.service_name}")
        print(f"  Status:  systemctl --user status {self.service_name}")
        print(f"  Logs:    journalctl --user -u {self.service_name} -f")
        
    def uninstall(self):
        """Uninstall the systemd service."""
        print("Uninstalling Trakt Discord Presence daemon...")
        
        # Stop service if running
        subprocess.run(["systemctl", "--user", "stop", self.service_name], 
                      stderr=subprocess.DEVNULL)
        
        # Disable service
        subprocess.run(["systemctl", "--user", "disable", self.service_name],
                      stderr=subprocess.DEVNULL)
        
        # Remove service file
        service_file = self.user_service_dir / self.service_name
        if service_file.exists():
            service_file.unlink()
            print(f"Removed service file: {service_file}")
        
        # Reload systemd
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        
        print("✅ Service uninstalled!")
    
    def start(self):
        """Start the service."""
        subprocess.run(["systemctl", "--user", "start", self.service_name], check=True)
        print("✅ Service started!")

    def stop(self):
        """Stop the service."""
        subprocess.run(["systemctl", "--user", "stop", self.service_name], check=True)
        print("✅ Service stopped!")
    
    def status(self):
        """Show service status."""
        subprocess.run(["systemctl", "--user", "status", self.service_name])
    
    def logs(self, follow=False):
        """Show service logs."""
        cmd = ["journalctl", "--user", "-u", self.service_name]
        if follow:
            cmd.append("-f")
        subprocess.run(cmd)

    def is_installed(self):
        """Check if service is installed."""
        service_file = self.user_service_dir / self.service_name
        return service_file.exists()

    def is_running(self):
        """Check if service is running."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", self.service_name],
                capture_output=True, text=True
            )
            return result.stdout.strip() == "active"
        except subprocess.CalledProcessError:
            return False

    def enable(self):
        subprocess.run(["systemctl", "--user", "enable", self.service_name], check=True)
        print("✅ Service enabled (will start on login).")

    def disable(self):
        subprocess.run(["systemctl", "--user", "disable", self.service_name], check=True)
        print("✅ Service disabled (won't start on login).")

class LaunchAgentInstaller:
    def __init__(self):
        self.label = "com.trakt.discord-presence"
        self.plist_name = f"{self.label}.plist"
        self.launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
        self.project_dir = Path(__file__).parent.absolute()
        self.venv_dir = self.project_dir / ".venv"
        self.main_script = self.project_dir / "main.py"
        self.logs_dir = self.project_dir / "logs"
        self.plist_path = self.launch_agents_dir / self.plist_name

    def check_requirements(self):
        if not shutil.which("launchctl"):
            raise RuntimeError("launchctl not found. This system doesn't support launchd.")
        if not self.main_script.exists():
            raise RuntimeError(f"main.py not found in {self.project_dir}")
        if not (self.project_dir / ".env").exists():
            raise RuntimeError(".env file not found. Please configure your credentials first.")

    def setup_venv(self):
        if not self.venv_dir.exists():
            print("Creating virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", str(self.venv_dir)], check=True)

        pip_path = self.venv_dir / "bin" / "pip"
        requirements_file = self.project_dir / "requirements.txt"
        if requirements_file.exists():
            print("Installing dependencies...")
            subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)
            subprocess.run([str(pip_path), "install", "-r", str(requirements_file)], check=True)

    def create_logs_dir(self):
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def create_plist(self):
        python_path = self.venv_dir / "bin" / "python"
        plist_content = textwrap.dedent(f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>Label</key>
                <string>{self.label}</string>
                <key>ProgramArguments</key>
                <array>
                    <string>{python_path}</string>
                    <string>{self.main_script}</string>
                </array>
                <key>WorkingDirectory</key>
                <string>{self.project_dir}</string>
                <key>RunAtLoad</key>
                <true/>
                <key>KeepAlive</key>
                <dict>
                    <key>SuccessfulExit</key>
                    <false/>
                </dict>
                <key>StandardOutPath</key>
                <string>{self.logs_dir / 'trakt-discord.log'}</string>
                <key>StandardErrorPath</key>
                <string>{self.logs_dir / 'trakt-discord-error.log'}</string>
                <key>EnvironmentVariables</key>
                <dict>
                    <key>PATH</key>
                    <string>/usr/local/bin:/usr/bin:/bin</string>
                </dict>
                <key>ThrottleInterval</key>
                <integer>10</integer>
            </dict>
            </plist>
        """)

        self.launch_agents_dir.mkdir(parents=True, exist_ok=True)
        self.plist_path.write_text(plist_content)
        print(f"Created LaunchAgent plist: {self.plist_path}")

    def load_agent(self):
        subprocess.run(["launchctl", "unload", str(self.plist_path)], stderr=subprocess.DEVNULL)
        subprocess.run(["launchctl", "load", str(self.plist_path)], check=True)

    def install(self):
        print("Installing Trakt Discord Presence LaunchAgent...")
        self.check_requirements()
        self.setup_venv()
        self.create_logs_dir()
        self.create_plist()
        self.load_agent()
        print("✅ LaunchAgent installed and started.")
        print("To view logs: tail -f", self.logs_dir / "trakt-discord.log")

    def uninstall(self):
        print("Uninstalling Trakt Discord Presence LaunchAgent...")
        if not self.plist_path.exists():
            print("ℹ️  LaunchAgent not installed. Nothing to uninstall.")
            return
        subprocess.run(["launchctl", "unload", str(self.plist_path)], stderr=subprocess.DEVNULL)
        if self.plist_path.exists():
            self.plist_path.unlink()
            print(f"Removed {self.plist_path}")
        print("✅ LaunchAgent uninstalled.")

    def start(self):
        subprocess.run(["launchctl", "load", str(self.plist_path)], check=True)
        print("✅ LaunchAgent started.")

    def stop(self):
        subprocess.run(["launchctl", "unload", str(self.plist_path)], check=True)
        print("✅ LaunchAgent stopped.")

    def restart(self):
        subprocess.run(["launchctl", "unload", str(self.plist_path)], stderr=subprocess.DEVNULL)
        subprocess.run(["launchctl", "load", str(self.plist_path)], check=True)
        print("✅ LaunchAgent restarted.")

    def status(self):
        if not self.plist_path.exists():
            print("❌ LaunchAgent is not installed.")
            return

        result = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
        running = False
        for line in result.stdout.splitlines():
            if self.label in line:
                parts = line.split()
                if parts and parts[0].isdigit():
                    print(f"✅ LaunchAgent running (PID {parts[0]})")
                else:
                    print("⚠️  LaunchAgent loaded but not currently running.")
                running = True
                break
        if not running:
            print("🔴 LaunchAgent not running. Use 'service.py start' to launch it.")

    def logs(self, follow=False):
        log_file = self.logs_dir / "trakt-discord.log"
        if not log_file.exists():
            print("No log file found at", log_file)
            return
        cmd = ["tail", "-n", "50"]
        if follow:
            cmd.append("-f")
        cmd.append(str(log_file))
        subprocess.run(cmd)

    def is_installed(self):
        return self.plist_path.exists()

    def is_running(self):
        result = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
        return self.label in result.stdout

    def enable(self):
        if not self.plist_path.exists():
            print("❌ LaunchAgent not installed. Install first with 'service.py install'.")
            return
        subprocess.run(["launchctl", "load", str(self.plist_path)], stderr=subprocess.DEVNULL)
        subprocess.run(["launchctl", "enable", "gui/{}/{}".format(os.getuid(), self.label)], stderr=subprocess.DEVNULL)
        print("✅ LaunchAgent enabled.")

    def disable(self):
        if not self.plist_path.exists():
            print("❌ LaunchAgent not installed.")
            return
        subprocess.run(["launchctl", "disable", "gui/{}/{}".format(os.getuid(), self.label)], stderr=subprocess.DEVNULL)
        subprocess.run(["launchctl", "unload", str(self.plist_path)], stderr=subprocess.DEVNULL)
        print("✅ LaunchAgent disabled.")


def main():
    parser = argparse.ArgumentParser(description="Trakt Discord Presence Daemon Manager")
    parser.add_argument("action", choices=[
        "install", "uninstall", "start", "stop", "status", "logs", "restart"
    ], help="Action to perform")
    parser.add_argument("-f", "--follow", action="store_true", 
                       help="Follow logs (only for 'logs' action)")
    
    args = parser.parse_args()
    
    if platform.system().lower() == "linux":
        installer = SystemdInstaller()
    elif platform.system().lower() == "darwin":
        installer = LaunchAgentInstaller()
    else:
        print(f"Unsupported platform: {platform.system()}" )
        sys.exit(1)
    
    try:
        if args.action == "install":
            installer.install()
        elif args.action == "uninstall":
            installer.uninstall()
        elif args.action == "start":
            installer.start()
        elif args.action == "stop":
            installer.stop()
        elif args.action == "restart":
            installer.restart()
        elif args.action == "status":
            installer.status()
        elif args.action == "logs":
            installer.logs(follow=args.follow)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
        sys.exit(0)

if __name__ == "__main__":
    main()
