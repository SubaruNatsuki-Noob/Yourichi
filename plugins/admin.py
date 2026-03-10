"""
Admin commands:
ban, unban, banlist, add_admin, deladmin, admins,
dlt_time, check_dlt_time, dbroadcast, pbroadcast, cmds
"""
import asyncio
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import OWNER_ID, CMD_TXT
from database.database import CosmicBotz
from helper import is_admin, is_owner, human_readable_time

router = Router()
logger = logging.getLogger(__name__)


def _target(message: Message):
    if message.reply_to_message:
        return message.reply_to_message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) == 2:
        try:
            return int(args[1])
        except ValueError:
            pass
    return None


# ── /ban ───────────────────────────────────────────────────────────────────────

@router.message(Command("ban"), is_admin)
async def ban_cmd(message: Message):
    uid = _target(message)
    if not uid:
        return await message.answer(
            "❌ Reply to a user or pass their ID.\nUsage: <code>/ban 123456789</code>"
        )
    if uid == OWNER_ID:
        return await message.answer("❌ Cannot ban the owner.")
    await CosmicBotz.add_ban_user(uid)
    await message.answer(f"🚫 User <code>{uid}</code> has been <b>banned</b>.")


# ── /unban ─────────────────────────────────────────────────────────────────────

@router.message(Command("unban"), is_admin)
async def unban_cmd(message: Message):
    uid = _target(message)
    if not uid:
        return await message.answer(
            "❌ Reply to a user or pass their ID.\nUsage: <code>/unban 123456789</code>"
        )
    await CosmicBotz.del_ban_user(uid)
    await message.answer(f"✅ User <code>{uid}</code> has been <b>unbanned</b>.")


# ── /banlist ───────────────────────────────────────────────────────────────────

@router.message(Command("banlist"), is_admin)
async def banlist_cmd(message: Message):
    banned = await CosmicBotz.get_ban_users()
    if not banned:
        return await message.answer("✅ No banned users.")
    lines = "\n".join(f"• <code>{uid}</code>" for uid in banned)
    await message.answer(f"<b>🚫 Banned Users ({len(banned)}):</b>\n\n{lines}")


# ── /add_admin ─────────────────────────────────────────────────────────────────

@router.message(Command("add_admin"), is_owner)
async def add_admin_cmd(message: Message):
    uid = _target(message)
    if not uid:
        return await message.answer("❌ Reply to a user or pass their ID.")
    await CosmicBotz.add_admin(uid)
    await message.answer(f"✅ <code>{uid}</code> is now an <b>admin</b>.")


# ── /deladmin ──────────────────────────────────────────────────────────────────

@router.message(Command("deladmin"), is_owner)
async def del_admin_cmd(message: Message):
    uid = _target(message)
    if not uid:
        return await message.answer("❌ Reply to a user or pass their ID.")
    await CosmicBotz.del_admin(uid)
    await message.answer(f"✅ <code>{uid}</code> removed from <b>admins</b>.")


# ── /admins ────────────────────────────────────────────────────────────────────

@router.message(Command("admins"), is_admin)
async def admins_cmd(message: Message):
    admins = await CosmicBotz.get_all_admins()
    text   = f"<b>👮 Admins:</b>\n\n• <code>{OWNER_ID}</code> (Owner)\n"
    for aid in admins:
        text += f"• <code>{aid}</code>\n"
    await message.answer(text)


# ── /dlt_time ──────────────────────────────────────────────────────────────────

@router.message(Command("dlt_time"), is_admin)
async def set_timer_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        return await message.answer(
            "❌ Usage: <code>/dlt_time &lt;seconds&gt;</code>\n"
            "Use <code>0</code> to disable auto-delete."
        )
    try:
        secs = int(args[1])
    except ValueError:
        return await message.answer("❌ Provide a valid number of seconds.")
    await CosmicBotz.set_del_timer(secs)
    label = human_readable_time(secs) if secs > 0 else "disabled"
    await message.answer(f"✅ Auto-delete timer set to <b>{label}</b>.")


# ── /check_dlt_time ────────────────────────────────────────────────────────────

@router.message(Command("check_dlt_time"), is_admin)
async def check_timer_cmd(message: Message):
    secs  = await CosmicBotz.get_del_timer()
    label = human_readable_time(secs) if secs > 0 else "disabled"
    await message.answer(f"⏱ <b>Auto-delete timer:</b> {label}")


# ── /dbroadcast ────────────────────────────────────────────────────────────────

@router.message(Command("dbroadcast"), is_admin)
async def dbroadcast_cmd(message: Message):
    reply = message.reply_to_message
    if not reply or not (reply.document or reply.video):
        return await message.answer("❌ Reply to a <b>document or video</b> to broadcast.")

    users  = await CosmicBotz.full_userbase()
    status = await message.answer(f"📤 Broadcasting to <b>{len(users)}</b> users...")
    ok, fail = 0, 0

    for uid in users:
        try:
            await reply.copy_to(uid)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)

    await status.edit_text(
        f"✅ <b>Broadcast complete!</b>\n\n👤 Success: {ok}\n❌ Failed: {fail}"
    )


# ── /pbroadcast ────────────────────────────────────────────────────────────────

@router.message(Command("pbroadcast"), is_admin)
async def pbroadcast_cmd(message: Message):
    reply = message.reply_to_message
    if not reply or not reply.photo:
        return await message.answer("❌ Reply to a <b>photo</b> to broadcast.")

    users  = await CosmicBotz.full_userbase()
    status = await message.answer(f"📤 Broadcasting photo to <b>{len(users)}</b> users...")
    ok, fail = 0, 0

    for uid in users:
        try:
            await reply.copy_to(uid)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)

    await status.edit_text(
        f"✅ <b>Photo broadcast complete!</b>\n\n👤 Success: {ok}\n❌ Failed: {fail}"
    )


# ── /cmds ──────────────────────────────────────────────────────────────────────

@router.message(Command("cmds"), is_admin)
async def cmds_cmd(message: Message):
    await message.answer(CMD_TXT)
