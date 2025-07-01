#!/usr/bin/env python3
"""
Linux systemd daemon installer and manager for Trakt Discord Presence.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse

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

def main():
    parser = argparse.ArgumentParser(description="Trakt Discord Presence Daemon Manager")
    parser.add_argument("action", choices=[
        "install", "uninstall", "start", "stop", "status", "logs", "restart"
    ], help="Action to perform")
    parser.add_argument("-f", "--follow", action="store_true", 
                       help="Follow logs (only for 'logs' action)")
    
    args = parser.parse_args()
    
    installer = SystemdInstaller()
    
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
            if installer.is_running():
                installer.stop()
            installer.start()
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
