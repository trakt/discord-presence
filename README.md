# Discord Trakt Presence Bot

🎬 **Automatically show what you're watching on Trakt.tv in your Discord status!**

This bot connects your [Trakt.tv](https://trakt.tv) account to Discord, displaying your current TV shows and movies as a "Watching" activity in your Discord profile.

## ✨ Features

- 🎭 **Proper "WATCHING" status** - Shows as "Watching [Show]" not "Playing [Show]"
- 🖼️ **Show artwork** - Displays movie/TV show posters as your activity image
- 🔄 **Auto-sync** - Updates every 15 seconds when you're watching something
- 🔌 **Reconnects automatically** - Handles Discord restarts and connection issues
- 📺 **TV Shows & Movies** - Works with both TV episodes and movies
- 🖥️ **Cross-platform** - Works on Windows, macOS, and Linux

## 🚀 Quick Start

### Prerequisites

- **Python 3.7+** - [Download here](https://www.python.org/downloads/)
- **Discord Desktop App** - Must be running on your computer
- **Trakt.tv account** - [Sign up free](https://trakt.tv/auth/join)

### Step 1: Download & Install

1. **Download this project:**
   ```bash
   git clone git@github.com:trakt/discord-presence.git
   cd discord-presence
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Step 2: Create a Trakt.tv App

1. **Go to Trakt.tv API settings:**
   - Visit: https://trakt.tv/oauth/applications
   - Click **"New Application"**

2. **Fill out the application form:**
   - **Name:** `Discord Presence` (or any name you like)
   - **Description:** `Shows my Trakt activity in Discord`
   - **Redirect URI:** `urn:ietf:wg:oauth:2.0:oob`
   - **Permissions:** None needed

3. **Save your credentials:**
   - After creating, you'll see:
     - **Client ID** - Copy this code
     - **Client Secret** - Copy this (keep it secret!  keep it safe!)
   - **Click on your app name** to see the **Application ID** (different from Client ID!).  Easiest way is to read the ID from the end of the URL.

### Step 3: Discord App (Optional - Default Provided)

**Good news!** This project includes a default Discord app called **"TV with Trakt"** that you can use immediately.

**Option A: Use the default app (recommended for beginners)**
- Skip this step! The default Discord Client ID is already in `.env.example`
- Your status will show as **"Watching TV with Trakt"**

**Option B: Create your own custom Discord app**
1. **Go to Discord Developer Portal:**
   - Visit: https://discord.com/developers/applications
   - Click **"New Application"**

2. **Create your application:**
   - **Name:** Choose any name (this appears in your Discord status)
   - Click **"Create"**

3. **Get your Discord Client ID:**
   - On the **"General Information"** page
   - Copy the **Application ID** (this is your Discord Client ID)
   - Replace the default value in your `.env` file

### Step 4: Configure the Bot

1. **Copy the example configuration:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the `.env` file** with your Trakt credentials:
   ```
   TRAKT_CLIENT_ID=your_trakt_client_id_here
   TRAKT_CLIENT_SECRET=your_trakt_client_secret_here
   TRAKT_APPLICATION_ID=your_trakt_application_id_here
   DISCORD_CLIENT_ID=1387827471822622850  # Default app (or use your own)
   ```

   **Note:** The Discord Client ID has a working default value. Only change it if you created your own Discord app.

### Step 5: Run the Bot

1. **Start the bot:**
   ```bash
   python main.py
   ```

2. **First-time setup:**
   - The bot will open a browser for Trakt.tv authentication
   - **Log in to Trakt.tv** and **authorize the app**
   - Copy the PIN code back to the terminal
   - Your credentials will be saved for future use

3. **Check Discord:**
   - Make sure Discord is running
   - Start watching something on Trakt.tv (check-in to a show/movie)
   - Your Discord status should update automatically!

## 📱 How to Use

### Check-in to Something on Trakt

1. **Go to Trakt.tv** or use the Trakt mobile app
2. **Find a TV show or movie** you're watching
3. **Click the "Check In" button** (▶️ icon)
4. **Your Discord status will update within 15 seconds!**

### What You'll See in Discord

```
🎬 Watching TV with Trakt
   Shark Tank
   S16E2 - Episode 2
   [Show poster image]
   Started watching 5 minutes ago
```

## 🛠️ Troubleshooting

### "Could not connect to Discord"
- ✅ Make sure Discord Desktop app is running (not just web browser)
- ✅ Restart Discord completely
- ✅ Try running the bot as administrator (Windows)

### "Authentication failed"
- ✅ Double-check your Trakt credentials in `.env`
- ✅ Make sure you copied the **Application ID** (not just Client ID)
- ✅ Verify redirect URI is exactly: `urn:ietf:wg:oauth:2.0:oob`

### "Not watching anything"
- ✅ Check-in to something on Trakt.tv first
- ✅ Make sure you're **actively checked in** (not just marked as watched)
- ✅ Try checking in to a different show/movie

### Discord shows "Playing" instead of "Watching"
- ✅ Make sure your Discord app is named "TV with Trakt"
- ✅ Restart Discord to clear cache
- ✅ Wait a few minutes for Discord to update

## 🔧 Advanced Configuration

### Running as a Daemon (Background Service)

**Cross-Platform - Automatic Installation:**

This project includes scripts to easily install the app as a daemon that starts automatically on login. The installer automatically detects your operating system:

```bash
# Install as daemon (runs automatically on login)
./scripts/install.sh

# Check daemon status and logs  
./scripts/status.sh

# Uninstall daemon (keeps project files)
./scripts/uninstall.sh
```

**Platform Support:**
- ✅ **macOS** - Uses LaunchAgents for proper user-level daemon management
- ✅ **Windows** - Uses Task Scheduler with PowerShell scripts  
- 🚧 **Linux** - Coming soon (systemd user services)

**What the daemon installer does:**
- ✅ Creates and activates Python virtual environment
- ✅ Installs all dependencies automatically
- ✅ Sets up auto-start on login (macOS: LaunchAgent, Windows: Task Scheduler)
- ✅ Creates log files for monitoring
- ✅ Handles automatic restarts if the app crashes
- ✅ Runs in background without terminal/command prompt window

**Manual Installation Examples:**

*Windows (Task Scheduler):*
1. Open Task Scheduler
2. Create Basic Task → Daily → Start at computer startup
3. Action: Start a program → Point to your Python installation and script

*Linux (systemd):*
```bash
# Create a systemd user service
systemctl --user enable trakt-discord-presence.service
```

### Custom Polling Interval

Edit `main.py` and change this line:
```python
time.sleep(15)  # Change 15 to your preferred seconds
```

## 📁 Project Structure

```
discord-presence/
├── main.py                                    # Main application
├── discord_ipc.py                            # Custom Discord integration
├── requirements.txt                           # Python dependencies
├── .env.example                               # Configuration template
├── .env                                       # Your credentials (keep private!)
├── scripts/                                   # Cross-platform daemon scripts
│   ├── install.sh                            # Universal installer (detects OS)
│   ├── status.sh                             # Universal status checker  
│   ├── uninstall.sh                          # Universal uninstaller
│   ├── macos/                                # macOS-specific files
│   │   ├── install.sh                        # macOS daemon installer
│   │   ├── uninstall.sh                      # macOS daemon uninstaller
│   │   ├── status.sh                         # macOS status checker
│   │   └── README.md                         # macOS documentation
│   ├── windows/                              # Windows-specific files
│   │   ├── install.ps1                      # Windows PowerShell installer
│   │   ├── uninstall.ps1                    # Windows PowerShell uninstaller
│   │   ├── status.ps1                       # Windows PowerShell status checker
│   │   ├── install.bat                      # Windows batch wrapper
│   │   ├── uninstall.bat                    # Windows batch wrapper
│   │   ├── status.bat                       # Windows batch wrapper
│   │   └── README.md                        # Windows documentation
│   └── linux/                                # Linux-specific files (coming soon)
│       └── README.md                         # Linux documentation
├── logs/                                      # Daemon log files (created by installer)
│   ├── trakt-discord.log                     # Application output
│   └── trakt-discord-error.log               # Error messages
└── README.md                                  # This file
```

## 🤝 Contributing

Found a bug or want to add a feature?

1. **Fork this repository**
2. **Create a feature branch:** `git checkout -b my-new-feature`
3. **Make your changes and test them**
4. **Submit a pull request**

## ⚠️ Security Note

**Never share your `.env` file or commit it to version control!** It contains your secret API keys.

The `.env` file is already in `.gitignore` to prevent accidental commits.

## 📄 License

This project is open source. Feel free to use, modify, and distribute!

## 🆘 Support

Having issues?

1. **Check the troubleshooting section above**
2. **Search existing GitHub issues**
3. **Create a new issue** with:
   - Your operating system
   - Python version (`python --version`)
   - Error messages (remove any API keys first!)

---

**Enjoy showing off what you're watching! 🍿**
