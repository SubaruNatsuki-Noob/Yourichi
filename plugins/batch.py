"""
Batch commands:

/batch        — Ask for first msg ID and last msg ID from DB channel → instant link
/custom_batch — Send multiple files directly to bot → /done → link (stored in DB channel)
/done         — Finish custom_batch session
/cancel       — Cancel any active session
/pro_batch    — Paste URLs, scan & sort by episode+quality, generate structured link set
"""
import re
import logging
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ContentType

from config import CHANNEL_ID
from database.database import CosmicBotz
from helper import is_admin, encode_file_id
from helper.utils import parse_tg_url
from helper.caption_parser import parse_filename

router = Router()
logger = logging.getLogger(__name__)

MEDIA_TYPES = {
    ContentType.DOCUMENT, ContentType.VIDEO, ContentType.AUDIO,
    ContentType.PHOTO, ContentType.ANIMATION, ContentType.VOICE, ContentType.VIDEO_NOTE,
}

# ── Session state ──────────────────────────────────────────────────────────────
# user_id -> {"mode": "custom"|"pro", "msg_ids": [], "step": ...}
_sessions: dict = {}
# user_id -> {"step": "first"|"last", "first_id": int}  (for /batch wizard)
_batch_wizard: dict = {}


# ── /batch — ask first & last msg ID ──────────────────────────────────────────

@router.message(Command("batch"), is_admin)
async def batch_cmd(message: Message):
    _batch_wizard[message.from_user.id] = {"step": "first"}
    await message.answer(
        "📦 <b>Batch Link Generator</b>\n\n"
        "Step 1/2 — Send the <b>first message ID</b> from your DB channel:"
    )


@router.message(is_admin, F.chat.type == "private", F.text.regexp(r"^\d+$"))
async def batch_wizard_input(message: Message, bot):
    uid   = message.from_user.id
    state = _batch_wizard.get(uid)

    if not state:
        return  # not in wizard

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
        # Log
        log_ch = await CosmicBotz.get_log_channel()
        if log_ch:
            try:
                await bot.send_message(
                    log_ch,
                    f"📦 <b>Batch link</b>\nFiles: {count} | IDs: {first_id}–{last_id}\n{link}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔗 Share", url=link)]
                    ]),
                    disable_web_page_preview=True,
                )
            except Exception:
                pass


# ── /custom_batch ──────────────────────────────────────────────────────────────

@router.message(Command("custom_batch"), is_admin)
async def custom_batch_cmd(message: Message):
    uid = message.from_user.id
    _sessions[uid] = {"mode": "custom", "msg_ids": []}
    await message.answer(
        "📁 <b>Custom Batch mode started!</b>\n\n"
        "Send or forward files here — I'll store each one automatically in the DB channel.\n\n"
        "When done → /done to get the link\n"
        "To abort → /cancel"
    )


# ── /done ──────────────────────────────────────────────────────────────────────

