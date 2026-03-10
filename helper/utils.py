import asyncio
import base64
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
    return base64.urlsafe_b64encode(str(msg_id).encode()).decode().rstrip("=")


def decode_file_id(encoded: str) -> int:
    pad = 4 - len(encoded) % 4
    return int(base64.urlsafe_b64decode(encoded + "=" * pad).decode())


def user_mention(user: User) -> str:
    name = user.full_name or str(user.id)
    return f'<a href="tg://user?id={user.id}">{name}</a>'


async def delete_messages_later(bot, chat_id: int, message_ids: list, delay: int):
    await asyncio.sleep(delay)
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
