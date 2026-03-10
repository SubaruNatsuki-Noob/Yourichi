"""
/help /about /stats /uptime + user reply guard
"""
import time
import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import HELP_TXT, USER_REPLY_TEXT, BOT_STATS_TEXT, OWNER_ID, OWNER
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
    if dy: parts.append(f"{dy}ᴅ")
    if h:  parts.append(f"{h}ʜ")
    if m:  parts.append(f"{m}ᴍ")
    parts.append(f"{s}ꜱ")
    return " ".join(parts)


@router.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(HELP_TXT)


@router.message(Command("about"))
async def about_cmd(message: Message, bot):
    me = await bot.get_me()
    text = (
        "<b><blockquote>"
        f"◈ ʙᴏᴛ: {me.full_name}\n"
        f"◈ ᴜꜱᴇʀɴᴀᴍᴇ: @{me.username}\n"
        "◈ ꜰʀᴀᴍᴇᴡᴏʀᴋ: Aiogram 3\n"
        "◈ ʟᴀɴɢᴜᴀɢᴇ: Python 3\n"
        f"◈ ᴅᴇᴠᴇʟᴏᴘᴇʀ: @{OWNER}\n"
        "</blockquote></b>"
    )
    await message.answer(text)


@router.message(Command("uptime"))
async def uptime_cmd(message: Message):
    await message.answer(BOT_STATS_TEXT.format(uptime=_uptime()))


@router.message(Command("stats"), is_admin)
async def stats_cmd(message: Message, bot):
    # Measure ping
    t0   = time.monotonic()
    sent = await message.answer("📡 ᴍᴇᴀꜱᴜʀɪɴɢ...")
    ping = round((time.monotonic() - t0) * 1000)

    users = len(await CosmicBotz.full_userbase())
    ban   = len(await CosmicBotz.get_ban_users())
    adm   = len(await CosmicBotz.get_all_admins())
    chs   = len(await CosmicBotz.show_channels())
    tm    = await CosmicBotz.get_del_timer()
    me    = await bot.get_me()

    await sent.edit_text(
        f"<b><blockquote>"
        f"◈ ʙᴏᴛ: {me.full_name}\n"
        f"◈ ᴘɪɴɢ: {ping}ᴍs\n"
        f"◈ ᴜᴘᴛɪᴍᴇ: {_uptime()}\n"
        f"◈ ᴜꜱᴇʀꜱ: {users}\n"
        f"◈ ʙᴀɴɴᴇᴅ: {ban}\n"
        f"◈ ᴀᴅᴍɪɴꜱ: {adm}\n"
        f"◈ ꜰꜱᴜʙ ᴄʜᴀɴɴᴇʟꜱ: {chs}\n"
        f"◈ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ: {human_readable_time(tm) if tm else 'ᴏꜰꜰ'}\n"
        f"</blockquote></b>"
    )


@router.message(F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def user_reply_guard(message: Message):
    uid = message.from_user.id
    if uid == OWNER_ID or await CosmicBotz.admin_exist(uid):
        return
    await message.answer(USER_REPLY_TEXT)
