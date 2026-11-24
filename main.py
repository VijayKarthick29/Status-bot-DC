from __future__ import annotations
import asyncio
import secrets
import hmac
import sys

# Windows consoles default to cp1252. Emoji channel names and custom emoji
# markdown must never crash a keeper cycle on the way to stdout.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
from contextlib import asynccontextmanager
from pathlib import Path

import discord
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field, field_validator

from config import settings
from bot.client import build_bot
from bot.discord_api import set_voice_status, DiscordAPIError
from bot.state import KeeperEntry

BASE_DIR = Path(__file__).resolve().parent
bot = build_bot()
bot_task: asyncio.Task | None = None
bot_error: str | None = None

async def _run_bot():
    """Run the gateway client and surface login failures instead of losing them."""
    global bot_error
    try:
        await bot.start(settings.discord_bot_token)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        bot_error = f"{type(exc).__name__}: {exc}"
        print(f"[BOT] Login failed -> {bot_error}", flush=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task
    bot_task = asyncio.create_task(_run_bot())
    yield
    if not bot.is_closed():
        await bot.close()
    if bot_task and not bot_task.done():
        bot_task.cancel()
        try:
            await bot_task
        except (asyncio.CancelledError, Exception):
            pass

app = FastAPI(title="VK VC STATUS BOT", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="vk_session",
    max_age=60 * 60 * 12,
    same_site="strict",
    https_only=settings.cookie_secure,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "dashboard" / "static"), name="static")

class StatusPayload(BaseModel):
    guild_id: int
    channel_id: int
    status: str = Field(default="", max_length=500)
    keep_status: bool = True
    stay_connected: bool = False

    @field_validator("guild_id", "channel_id", mode="before")
    @classmethod
    def _coerce_snowflake(cls, value):
        # Discord snowflakes exceed JS's safe integer range, so accept strings and
        # parse them here where Python's int is arbitrary precision.
        if isinstance(value, str):
            value = value.strip()
            if not value.isdigit():
                raise ValueError("Invalid Discord ID.")
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValueError("Invalid Discord ID.")

def require_auth(request: Request, check_csrf: bool = True):
    if request.session.get("authenticated") is not True:
        raise HTTPException(status_code=401, detail="Please log in again.")
    if check_csrf:
        csrf = request.headers.get("x-csrf-token", "")
        expected = request.session.get("csrf", "")
        if not csrf or not expected or not hmac.compare_digest(csrf, expected):
            raise HTTPException(status_code=403, detail="Security token check failed. Refresh the page and try again.")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    html = (BASE_DIR / "dashboard" / "templates" / "index.html").read_text(encoding="utf-8")
    if request.session.get("authenticated") is True:
        csrf = request.session.get("csrf", "")
        html = html.replace("__CSRF_TOKEN__", csrf).replace("__AUTH_STATE__", "true")
    else:
        html = html.replace("__CSRF_TOKEN__", "").replace("__AUTH_STATE__", "false")
    return HTMLResponse(html)

@app.post("/api/login")
async def login(request: Request, password: str = Form(...)):
    if not hmac.compare_digest(password.encode("utf-8"), settings.dashboard_password.encode("utf-8")):
        # Small generic response; do not reveal which credential was wrong.
        raise HTTPException(status_code=401, detail="Incorrect password.")
    request.session.clear()
    request.session["authenticated"] = True
    request.session["csrf"] = secrets.token_urlsafe(32)
    return {"ok": True}

@app.post("/api/logout")
async def logout(request: Request):
    require_auth(request)
    request.session.clear()
    return {"ok": True}

@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "bot_ready": bot.is_ready(),
        "bot_user": str(bot.user) if bot.user else None,
        "bot_error": bot_error,
        "keepers": len(bot.state.all()),
        "voice_connections": [
            {"channel_id": str(vc.channel.id), "channel_name": vc.channel.name}
            for vc in bot.voice_clients if vc.channel
        ],
        "last_keeper_run": bot.last_keeper_run,
        "keeper_errors": bot.keeper_errors[:5],
        "keeper_interval": settings.keeper_interval,
        "restores": bot.restores,
        "observed_statuses": {
            str(k): v[0] for k, v in bot.observed_status.items()
        },
    }

@app.get("/health")
async def health_alias():
    return {"ok": True}

@app.get("/api/servers")
async def servers(request: Request):
    require_auth(request, check_csrf=False)
    return [{"id": str(g.id), "name": g.name} for g in bot.guilds]

@app.get("/api/servers/{guild_id}/channels")
async def channels(guild_id: int, request: Request):
    require_auth(request, check_csrf=False)
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(404, "Server not found. Make sure the bot is invited and online.")
    allowed = (discord.VoiceChannel, discord.StageChannel)
    return [{"id": str(c.id), "name": c.name, "type": "Stage" if isinstance(c, discord.StageChannel) else "Voice"}
            for c in guild.channels if isinstance(c, allowed)]

@app.get("/api/servers/{guild_id}/emojis")
async def emojis(guild_id: int, request: Request):
    require_auth(request, check_csrf=False)
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise HTTPException(404, "Server not found. Make sure the bot is invited and online.")
    result = []
    for emoji in guild.emojis:
        prefix = "a" if emoji.animated else ""
        result.append({
            "name": emoji.name,
            "id": str(emoji.id),
            "animated": emoji.animated,
            "markdown": f"<{prefix}:{emoji.name}:{emoji.id}>",
            "url": str(emoji.url),
        })
    return sorted(result, key=lambda e: e["name"].lower())


@app.get("/api/keepers")
async def keepers(request: Request):
    require_auth(request, check_csrf=False)
    result = []
    for entry in bot.state.all():
        channel = bot.get_channel(int(entry.channel_id))
        result.append({
            **entry.__dict__,
            "channel_name": channel.name if channel else "Unavailable",
            "connected": any(vc.channel and vc.channel.id == int(entry.channel_id) for vc in bot.voice_clients),
        })
    return result


@app.delete("/api/keepers/{channel_id}")
async def remove_keeper(channel_id: int, request: Request):
    require_auth(request)
    entry = bot.state.remove(channel_id)
    try:
        await set_voice_status(settings.discord_bot_token, channel_id, None)
    except DiscordAPIError:
        pass
    await bot.disconnect_channel(channel_id)
    return {"ok": True, "removed": entry is not None}


@app.post("/api/status")
async def update_status(payload: StatusPayload, request: Request):
    require_auth(request)
    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        raise HTTPException(404, "Bot is not in that server, or it is still connecting. Refresh and try again.")
    channel = guild.get_channel(payload.channel_id)
    if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
        raise HTTPException(400, "Select a voice or stage channel.")
    try:
        await set_voice_status(settings.discord_bot_token, channel.id, payload.status or None)
    except DiscordAPIError as exc:
        raise HTTPException(400, str(exc))

    if payload.keep_status or payload.stay_connected:
        bot.state.set(KeeperEntry(
            guild_id=str(payload.guild_id),
            channel_id=str(payload.channel_id),
            status=payload.status,
            keep_status=payload.keep_status,
            stay_connected=payload.stay_connected,
        ))
    else:
        bot.state.remove(payload.channel_id)

    warning = None
    if payload.stay_connected and not any(
        vc.channel and vc.channel.id == channel.id for vc in bot.voice_clients
    ):
        try:
            await channel.connect(reconnect=True, timeout=20)
        except Exception as exc:
            warning = f"Could not join voice channel yet: {type(exc).__name__}: {exc}"
            bot._record_error(warning)
    elif not payload.stay_connected:
        await bot.disconnect_channel(channel.id)

    return {
        "ok": True,
        "message": "Status cleared." if not payload.status else "Status updated.",
        "warning": warning,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
