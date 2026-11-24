from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class KeeperEntry:
    guild_id: str
    channel_id: str
    status: str
    keep_status: bool
    stay_connected: bool


class KeeperState:
    """On-disk record of statuses and voice sessions that must stay alive."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._data: dict[str, dict] = {"channels": {}}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            channels = raw.get("channels", {})
            if isinstance(channels, dict):
                self._data["channels"] = channels
        except (OSError, ValueError):
            # A corrupt state file should not stop the bot from booting.
            pass

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def all(self) -> list[KeeperEntry]:
        with self._lock:
            return [
                KeeperEntry(
                    guild_id=str(v.get("guild_id", "")),
                    channel_id=str(k),
                    status=str(v.get("status") or ""),
                    keep_status=bool(v.get("keep_status")),
                    stay_connected=bool(v.get("stay_connected")),
                )
                for k, v in self._data["channels"].items()
            ]

    def get(self, channel_id: int | str) -> KeeperEntry | None:
        with self._lock:
            v = self._data["channels"].get(str(channel_id))
        if v is None:
            return None
        return KeeperEntry(
            guild_id=str(v.get("guild_id", "")),
            channel_id=str(channel_id),
            status=str(v.get("status") or ""),
            keep_status=bool(v.get("keep_status")),
            stay_connected=bool(v.get("stay_connected")),
        )

    def set(self, entry: KeeperEntry) -> None:
        with self._lock:
            self._data["channels"][entry.channel_id] = asdict(entry)
            self._save()

    def remove(self, channel_id: int | str) -> KeeperEntry | None:
        entry = self.get(channel_id)
        with self._lock:
            self._data["channels"].pop(str(channel_id), None)
            self._save()
        return entry
