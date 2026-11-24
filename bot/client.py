from __future__ import annotations

import asyncio
import time
from pathlib import Path

import discord
from discord.ext import commands

from config import settings
from bot.discord_api import set_voice_status
from bot.state import KeeperState


def _print(text: str) -> None:
    """Print without letting a legacy console codepage kill a keeper cycle."""
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        print(text.encode("utf-8", "backslashreplace").decode("ascii"), flush=True)


class VKBot(commands.Bot):
    def __init__(self, state: KeeperState):
        intents = discord.Intents.default()
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)
        self.state = state
        self.keeper_task: asyncio.Task | None = None
        self.last_keeper_run: float | None = None
        self.keeper_errors: list[str] = []
        self.restores = 0
        self.observed_status: dict[int, tuple[str, float]] = {}
        self._status_last_apply: dict[int, float] = {}
        self._restore_tasks: dict[int, asyncio.Task] = {}

    async def setup_hook(self):
        await self.load_extension("bot.commands")
        await self.tree.sync()
        self._install_status_hook()

    def _install_status_hook(self) -> None:
        """discord.py has no voice-status event, so hook the raw gateway parser."""
        parsers = self._connection.parsers
        key = "VOICE_CHANNEL_STATUS_UPDATE"
        original = parsers.get(key)

        def hooked(data):
            if original is not None:
                original(data)
            self._status_event(data)

        parsers[key] = hooked

    def _status_event(self, data: dict) -> None:
        try:
            channel_id = int(data["id"])
        except (KeyError, TypeError, ValueError):
            return
        status = data.get("status") or ""
        self.observed_status[channel_id] = (status, time.time())

        entry = self.state.get(channel_id)
        if entry is None or not entry.keep_status:
            return
        if status == entry.status:
            return
        # Ignore our own write settling and avoid stacking restores.
        if time.time() - self._status_last_apply.get(channel_id, 0) < 3:
            return
        pending = self._restore_tasks.get(channel_id)
        if pending and not pending.done():
            return
        self._restore_tasks[channel_id] = asyncio.create_task(self._restore_one(channel_id))

    async def _restore_one(self, channel_id: int) -> None:
        await asyncio.sleep(0.4)
        entry = self.state.get(channel_id)
        if entry is None or not entry.keep_status or not entry.status:
            return
        observed, _ = self.observed_status.get(channel_id, ("", 0))
        if observed == entry.status:
            return
        try:
            await set_voice_status(settings.discord_bot_token, channel_id, entry.status)
        except Exception as exc:
            self._record_error(f"restore {channel_id}: {type(exc).__name__}: {exc}")
            return
        self._status_last_apply[channel_id] = time.time()
        self.restores += 1
        channel = self.get_channel(channel_id)
        name = channel.name if channel else str(channel_id)
        _print(f"[KEEPER] Restored emojis in {name} ({channel_id})")

    async def on_ready(self):
        _print(f"[BOT] Logged in as {self.user} (ID: {self.user.id})")
        if self.keeper_task is None or self.keeper_task.done():
            self.keeper_task = asyncio.create_task(self._keeper_loop())

    async def on_disconnect(self):
        _print("[BOT] Gateway disconnected — keeper will restore sessions on reconnect.")

    async def apply_keepers(self) -> None:
        """Re-assert every saved status and voice session once."""
        for entry in self.state.all():
            channel = self.get_channel(int(entry.channel_id))
            if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                continue

            if entry.stay_connected and not any(
                vc.channel and vc.channel.id == channel.id for vc in self.voice_clients
            ):
                try:
                    await channel.connect(reconnect=True, timeout=20)
                    _print(f"[KEEPER] Joined {channel.name} ({channel.id})")
                except Exception as exc:
                    self._record_error(f"join {channel.id}: {type(exc).__name__}: {exc}")

            if entry.keep_status and entry.status:
                try:
                    await set_voice_status(settings.discord_bot_token, channel.id, entry.status)
                    self._status_last_apply[channel.id] = time.time()
                    _print(f"[KEEPER] Re-applied status in {channel.name} ({channel.id})")
                except Exception as exc:
                    self._record_error(f"status {channel.id}: {type(exc).__name__}: {exc}")

        self.last_keeper_run = time.time()

    def _record_error(self, message: str) -> None:
        _print(f"[KEEPER] {message}")
        self.keeper_errors.insert(0, message)
        del self.keeper_errors[10:]

    async def _keeper_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                await self.apply_keepers()
            except Exception as exc:
                self._record_error(f"loop: {type(exc).__name__}: {exc}")
            await asyncio.sleep(max(30, settings.keeper_interval))

    async def disconnect_channel(self, channel_id: int) -> None:
        for vc in list(self.voice_clients):
            if vc.channel and vc.channel.id == channel_id:
                await vc.disconnect(force=True)


def build_bot() -> VKBot:
    state = KeeperState(Path(settings.state_path).resolve())
    return VKBot(state)
