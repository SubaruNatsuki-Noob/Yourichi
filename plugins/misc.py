"""
Misc: /help, /about, /stats, /uptime + user reply guard.
All original config texts preserved.
"""
import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import (
    HELP_TXT, ABOUT_TXT,
    USER_REPLY_TEXT, BOT_STATS_TEXT,
    OWNER_ID,
)
from database.database import CosmicBotz
from helper import is_admin

router = Router()

_START_TIME = datetime.datetime.now(datetime.timezone.utc)


def _uptime() -> str:
    delta      = datetime.datetime.now(datetime.timezone.utc) - _START_TIME
    hours, r   = divmod(int(delta.total_seconds()), 3600)
    mins, secs = divmod(r, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days:  parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if mins:  parts.append(f"{mins}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


@router.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(HELP_TXT)


@router.message(Command("about"))
async def about_cmd(message: Message):
    await message.answer(ABOUT_TXT)


@router.message(Command("stats"), is_admin)
async def stats_cmd(message: Message):
    users    = len(await CosmicBotz.full_userbase())
    banned   = len(await CosmicBotz.get_ban_users())
    admins   = len(await CosmicBotz.get_all_admins())
    channels = len(await CosmicBotz.show_channels())
    await message.answer(
        f"<b>📊 Bot Stats</b>\n\n"
        f"👤 Users: <b>{users}</b>\n"
        f"🚫 Banned: <b>{banned}</b>\n"
        f"👮 Admins: <b>{admins}</b>\n"
        f"📢 FSub channels: <b>{channels}</b>\n"
        f"⏱ Uptime: <b>{_uptime()}</b>"
    )


@router.message(Command("uptime"))
async def uptime_cmd(message: Message):
    await message.answer(BOT_STATS_TEXT.format(uptime=_uptime()))


# ── User reply guard ───────────────────────────────────────────────────────────
# Non-admin sends plain text in private → USER_REPLY_TEXT (original behaviour)

@router.message(F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def user_reply_guard(message: Message):
    uid = message.from_user.id
    # Admins are handled by batch/custom_batch text collectors — skip here
    if uid == OWNER_ID or await CosmicBotz.admin_exist(uid):
        return
    await message.answer(USER_REPLY_TEXT)
