import base64
import struct
import logging
from datetime import datetime
import pytz
from aiogram.types import User

logger = logging.getLogger(__name__)


def get_ist_time() -> datetime:
    return datetime.now(pytz.timezone("Asia/Kolkata"))


def human_readable_time(seconds: int) -> str:
    if seconds <= 0:
        return "disabled"
    periods = [("day", 86400), ("hour", 3600), ("minute", 60), ("second", 1)]
    parts = []
    for name, secs in periods:
        val, seconds = divmod(seconds, secs)
        if val:
            parts.append(f"{val} {name}{'s' if val != 1 else ''}")
    return ", ".join(parts) if parts else "0 seconds"


def encode_file_id(msg_id: int) -> str:
    """
    Encode msg_id as Telegram-style base64.
    Packs as 8-byte big-endian → base64url → looks like BQADAQAD8AkAAp...
    Example: msg_id 12345 → AAAAAAAAADk
    """
    raw     = struct.pack(">q", msg_id)
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return encoded


def decode_file_id(encoded: str) -> int:
    """Decode back to msg_id. Handles both new (8-byte) and legacy (plain text) encoding."""
    pad = 4 - len(encoded) % 4
    raw = base64.urlsafe_b64decode(encoded + "=" * pad)
    if len(raw) == 8:
        return struct.unpack(">q", raw)[0]
    return int(raw.decode())  # legacy fallback


def user_mention(user: User) -> str:
    name = user.full_name or str(user.id)
    return f'<a href="tg://user?id={user.id}">{name}</a>'


def parse_tg_url(url: str) -> tuple:
    """
    Parse a Telegram post URL into (chat_identifier, message_id).
    Supports:
      https://t.me/channelname/123
      https://t.me/c/1234567890/123  (private channel)
    Returns (chat_ref, msg_id) or (None, None) on failure.
    """
    try:
        url   = url.strip().rstrip("/")
        path  = url.replace("https://t.me/", "").replace("http://t.me/", "")
        parts = path.split("/")
        if parts[0] == "c" and len(parts) >= 3:
            return f"-100{parts[1]}", int(parts[2])
        elif len(parts) >= 2:
            return parts[0], int(parts[1])
    except Exception:
        pass
    return None, None
