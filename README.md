# ⟡ VK VC STATUS BOT

**Automated Discord Voice Channel Status Manager & 24/7 Keeper**

A powerful Python Discord bot with slash commands and a sleek private black-purple web dashboard for managing, setting, and continuously maintaining voice-channel statuses alive 24/7. Supports local Windows hosting and cloud deployment.

---

## ✨ Features

- **24/7 Voice Status Keeper:** Automatically detects when channel status is dropped or changed and restores it within milliseconds.
- **24/7 Stay-Connected Voice Client:** Keeps the bot connected to chosen voice channels with automatic reconnection.
- **Modern Glass Web Dashboard:** Dark purple & black glassmorphic UI for live monitoring, server selection, emoji insertion, and status management.
- **Custom Server Emojis Support:** Full picker for animated and static emojis from connected servers.
- **Discord Slash Commands:** Native `/vcstatus`, `/vcreset`, and `/vchelp` commands.
- **Robust Security:** Signed session cookies, CSRF protection, and strict rate limiting.
- **Cloud & Local Ready:** Pre-configured for local Windows hosting, Docker, and Render blueprint deployment.

---

## 📁 Project Structure

```text
VK-VC-STATUS-BOT/
├── bot/
│   ├── client.py          # Discord client with raw gateway voice status listener
│   ├── commands.py        # Slash commands (/vcstatus, /vcreset, /vchelp)
│   ├── discord_api.py     # Discord API v10 voice status updater
│   └── state.py           # Thread-safe persistent keeper state
├── dashboard/
│   ├── static/
│   │   ├── app.js         # Dashboard frontend logic & API client
│   │   └── style.css      # Custom dark/purple dashboard styles
│   └── templates/
│       └── index.html     # Glassmorphic control panel interface
├── config.py              # Environment configuration & validation
├── Dockerfile             # Container configuration
├── LICENSE                # MIT License
├── main.py                # FastAPI server & bot lifespan manager
├── README.md              # Documentation
├── render.yaml            # Render cloud deployment blueprint
├── requirements.txt       # Dependencies
└── run-24-7.ps1           # Windows watchdog script for 24/7 uptime
```

---

## ⚙️ Requirements

- Python 3.11 or newer (Python 3.12 recommended)
- A Discord application and bot created in the [Discord Developer Portal](https://discord.com/developers/applications)
- The bot invited to your server with appropriate permissions

---

## 🚀 Setup Guide

### 1. Configure Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create an application.
2. Under **Bot**, create or reset your bot token and copy it securely.
3. Under **OAuth2 > URL Generator**, select scopes `bot` and `applications.commands`.
4. Grant the bot permissions:
   - `View Channels`
   - `Manage Channels`
   - `Connect` & `Speak` (if using 24/7 voice connection)
   - `Set Voice Channel Status` (if listed in your portal UI)
5. Invite the bot to your target server using the generated URL.

> **Permission Note:** Discord's voice status endpoint requires `SET_VOICE_CHANNEL_STATUS`. When updating status without being connected to the channel, Discord additionally requires `MANAGE_CHANNELS`.

### 2. Run Locally on Windows

Open PowerShell in the project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Fill in your `.env` configuration:
- `DISCORD_BOT_TOKEN`: Your Discord bot token
- `DASHBOARD_PASSWORD`: Secure dashboard password (at least 11 characters)
- `SESSION_SECRET`: 32+ random characters secret key

Start the bot and dashboard:

```powershell
python main.py
```

Open `http://127.0.0.1:8000` in your browser and log in with your dashboard password.

---

## 🤖 Bot Commands

| Command | Description |
|---|---|
| `/vcstatus text:<message>` | Set custom status on your current voice channel |
| `/vcreset` | Clear the current voice channel's status |
| `/vchelp` | Display bot commands and help overview |

---

## ☁️ Cloud Deployment (Render)

1. Push this repository to GitHub.
2. In Render, select **New > Blueprint** and link your repository.
3. Configure the environment variables:
   - `DISCORD_BOT_TOKEN`
   - `DASHBOARD_PASSWORD`
   - `PUBLIC_BASE_URL` (e.g. `https://vk-vc-status-bot.onrender.com`)
4. Deploy the blueprint. The bot and dashboard will boot into production.

---

## 🔒 Security Checklist

- Never commit or publicly share `.env` or your Discord bot token.
- `.env`, `.venv`, and `keeper_state.json` are excluded via `.gitignore`.
- Always use HTTPS in cloud deployments (`COOKIE_SECURE=true`).
- Keep your dashboard password strong and private.

---

## 👨‍💻 Developer

**Vijay Karthick**

Developer | Security Researcher | System Architect

GitHub: [@VijayKarthick29](https://github.com/VijayKarthick29)

---

*Built with Python & FastAPI. Designed for automation and persistence.*

⭐ If you find this project interesting, consider starring the repository.
