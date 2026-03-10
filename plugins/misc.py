"""
/help /about /stats /uptime + user reply guard
"""
import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import HELP_TXT, ABOUT_TXT, USER_REPLY_TEXT, BOT_STATS_TEXT, OWNER_ID
from database.database import CosmicBotz
from helper import is_admin, human_readable_time

router = Router()
_START = datetime.datetime.now(datetime.timezone.utc)


def _uptime() -> str:
    d     = datetime.datetime.now(datetime.timezone.utc) - _START
    h, r  = divmod(int(d.total_seconds()), 3600)
    m, s  = divmod(r, 60)
    dy, h = divmod(h, 24)
    parts = []
    if dy: parts.append(f"{dy}d")
    if h:  parts.append(f"{h}h")
    if m:  parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


@router.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(HELP_TXT)

@router.message(Command("about"))
async def about_cmd(message: Message):
    await message.answer(ABOUT_TXT)

@router.message(Command("uptime"))
async def uptime_cmd(message: Message):
    await message.answer(BOT_STATS_TEXT.format(uptime=_uptime()))

@router.message(Command("stats"), is_admin)
async def stats_cmd(message: Message):
    users = len(await CosmicBotz.full_userbase())
    ban   = len(await CosmicBotz.get_ban_users())
    adm   = len(await CosmicBotz.get_all_admins())
    chs   = len(await CosmicBotz.show_channels())
    tm    = await CosmicBotz.get_del_timer()
    await message.answer(
        f"<b>📊 Bot Stats</b>\n\n"
        f"👤 Users: <b>{users}</b>\n🚫 Banned: <b>{ban}</b>\n"
        f"👮 Admins: <b>{adm}</b>\n📢 FSub: <b>{chs}</b>\n"
        f"⏱ Timer: <b>{human_readable_time(tm) if tm else 'Off'}</b>\n"
        f"🕐 Uptime: <b>{_uptime()}</b>"
    )

@router.message(F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def user_reply_guard(message: Message):
    uid = message.from_user.id
    if uid == OWNER_ID or await CosmicBotz.admin_exist(uid):
        return
    await message.answer(USER_REPLY_TEXT)
