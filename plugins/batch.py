import re
import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ContentType

from config import CHANNEL_ID
from database.database import CosmicBotz
from helper import is_admin, encode_file_id
# Assuming these exist in your helper modules based on your snippet
from helper.utils import parse_tg_url
from helper.caption_parser import parse_filename

router = Router()
logger = logging.getLogger(__name__)

MEDIA_TYPES = {
    ContentType.DOCUMENT, ContentType.VIDEO, ContentType.AUDIO,
    ContentType.PHOTO, ContentType.ANIMATION, ContentType.VOICE, ContentType.VIDEO_NOTE,
}

# ── Session state ──────────────────────────────────────────────────────────────
# user_id -> {"mode": "custom", "msg_ids": []}
_sessions: dict = {}
# user_id -> {"step": "first"|"last", "first_id": int}
_batch_wizard: dict = {}


# ── /batch — ask first & last msg ID ──────────────────────────────────────────

@router.message(Command("batch"), is_admin)
async def batch_cmd(message: Message):
    _batch_wizard[message.from_user.id] = {"step": "first"}
    await message.answer(
        "📦 <b>Batch Link Generator</b>\n\n"
        "Step 1/2 — Send the <b>first message ID</b> from your DB channel:"
    )

# FIXED: Added lambda filter to ensure it only catches numbers IF user is in a session
@router.message(
    is_admin, 
    F.chat.type == "private", 
    F.text.regexp(r"^\d+$"),
    lambda message: message.from_user.id in _batch_wizard
)
async def batch_wizard_input(message: Message, bot: Bot):
    uid = message.from_user.id
    state = _batch_wizard[uid]
    msg_id = int(message.text.strip())

    if state["step"] == "first":
        _batch_wizard[uid] = {"step": "last", "first_id": msg_id}
        await message.answer(
            f"✅ First ID: <code>{msg_id}</code>\n\n"
            f"Step 2/2 — Now send the <b>last message ID</b>:"
        )

    elif state["step"] == "last":
        first_id = state["first_id"]
        last_id  = msg_id
        del _batch_wizard[uid]

        if last_id < first_id:
            first_id, last_id = last_id, first_id

        param = f"batch_{first_id}_{last_id}"
        me    = await bot.get_me()
        link  = f"https://t.me/{me.username}?start={param}"
        count = last_id - first_id + 1

        await message.answer(
            f"✅ <b>Batch link created!</b>\n\n"
            f"📦 Files: <b>{count}</b> (IDs {first_id}–{last_id})\n"
            f"🔗 {link}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Share Link", url=link)]
            ]),
            disable_web_page_preview=True,
        )
        
        # Log to log channel
        log_ch = await CosmicBotz.get_log_channel()
        if log_ch:
            try:
                await bot.send_message(
                    log_ch,
                    f"📦 <b>Batch link</b>\nFiles: {count} | IDs: {first_id}–{last_id}\n{link}",
                    disable_web_page_preview=True
                )
            except Exception: pass


# ── /custom_batch ──────────────────────────────────────────────────────────────

@router.message(Command("custom_batch"), is_admin)
async def custom_batch_cmd(message: Message):
    uid = message.from_user.id
    _sessions[uid] = {"mode": "custom", "msg_ids": []}
    await message.answer(
        "📁 <b>Custom Batch mode started!</b>\n\n"
        "Send or forward files here — I'll store each one automatically.\n\n"
        "When done → /done\n"
        "To abort → /cancel"
    )

# FIXED: Added lambda filter so it doesn't accidentally steal files meant for other routers
@router.message(
    is_admin, 
    F.content_type.in_(MEDIA_TYPES),
    lambda message: message.from_user.id in _sessions
)
async def handle_custom_batch_files(message: Message):
    uid = message.from_user.id
    # Logic to forward to CHANNEL_ID and save IDs
    try:
        fwd = await message.forward(CHANNEL_ID)
        _sessions[uid]["msg_ids"].append(fwd.message_id)
        # Optional: Send a small reaction or ack
    except Exception as e:
        await message.answer(f"❌ Error: {e}")


# ── /done & /cancel ────────────────────────────────────────────────────────────

@router.message(Command("done"), is_admin)
async def done_cmd(message: Message, bot: Bot):
    uid = message.from_user.id
    session = _sessions.get(uid)
    
    if not session or not session["msg_ids"]:
        return await message.answer("❌ No active session or no files sent.")
    
    msg_ids = session["msg_ids"]
    first_id, last_id = msg_ids[0], msg_ids[-1]
    del _sessions[uid]
    
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=batch_{first_id}_{last_id}"
    
    await message.answer(
        f"✅ <b>Custom Batch Complete!</b>\n"
        f"Total files: {len(msg_ids)}\n\n🔗 {link}"
    )

@router.message(Command("cancel"), is_admin)
async def cancel_cmd(message: Message):
    uid = message.from_user.id
    if uid in _sessions: del _sessions[uid]
    if uid in _batch_wizard: del _batch_wizard[uid]
    await message.answer("Process cancelled. States cleared. ✅")
