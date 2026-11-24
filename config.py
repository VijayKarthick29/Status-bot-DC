from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    discord_bot_token: str = os.getenv("DISCORD_BOT_TOKEN", "")
    dashboard_password: str = os.getenv("DASHBOARD_PASSWORD", "")
    session_secret: str = os.getenv("SESSION_SECRET", "")
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    keeper_interval: int = int(os.getenv("STATUS_KEEP_INTERVAL", "600"))
    state_path: str = os.getenv("STATE_PATH", "keeper_state.json")

settings = Settings()

_PLACEHOLDER_TOKENS = {"PASTE_YOUR_BOT_TOKEN_HERE", "replace-with-your-discord-bot-token"}

if not settings.discord_bot_token:
    raise RuntimeError("DISCORD_BOT_TOKEN is missing. Copy .env.example to .env and configure it.")
if settings.discord_bot_token in _PLACEHOLDER_TOKENS:
    print("[CONFIG] DISCORD_BOT_TOKEN is still a placeholder. The dashboard will run, but the bot will stay offline.", flush=True)
if len(settings.dashboard_password) < 11:
    raise RuntimeError("Set DASHBOARD_PASSWORD to a password of at least 11 characters.")
if len(settings.session_secret) < 32:
    raise RuntimeError("Set SESSION_SECRET to a random secret of at least 32 characters.")
