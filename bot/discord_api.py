from __future__ import annotations
import aiohttp

API_BASE = "https://discord.com/api/v10"

class DiscordAPIError(Exception):
    pass

async def set_voice_status(token: str, channel_id: int, status: str | None):
    """Set or clear a voice channel status using Discord's bot API."""
    url = f"{API_BASE}/channels/{channel_id}/voice-status"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.put(url, headers=headers, json={"status": status}) as response:
            if response.status == 204:
                return
            try:
                body = await response.json()
            except Exception:
                body = {"message": await response.text()}
            message = body.get("message", "Discord API request failed")
            code = body.get("code")
            raise DiscordAPIError(f"Discord returned HTTP {response.status}: {message} (code: {code})")
