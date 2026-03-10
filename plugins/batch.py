"""
Batch upload handlers.

/batch        — session mode: send files one by one → /done for link
/custom_batch — specific message IDs mode → /done for link
/done         — finish active session and generate link
/cancel       — abort current session
"""
import functools
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import CHANNEL_ID
from database.database import CosmicBotz
from helper import is_admin

router = Router()
logger = logging.getLogger(__name__)

MEDIA_TYPES = {"document", "video", "audio", "photo", "animation", "voice", "video_note"}

# user_id -> {"mode": "batch"|"custom", "msg_ids": [...]}
_sessions: dict = {}


# ── /batch ─────────────────────────────────────────────────────────────────────

@router.message(Command("batch"), is_admin)
@functools.wraps(lambda m, **kw: None)
async def start_batch(message: Message):
    _sessions[message.from_user.id] = {"mode": "batch", "msg_ids": []}
    await message.answer(
        "📦 <b>Batch mode started!</b>\n\n"
        "Send or forward files one by one. I'll store each one automatically.\n\n"
        "Send /done when finished to get the link.\n"
        "Send /cancel to abort."
    )


# ── /custom_batch ──────────────────────────────────────────────────────────────

@router.message(Command("custom_batch"), is_admin)
@functools.wraps(lambda m, **kw: None)
async def start_custom_batch(message: Message):
    """
    Option A — inline IDs: /custom_batch 101 105 112
    Option B — interactive: /custom_batch  then send IDs as text
    """
    uid  = message.from_user.id
    args = message.text.split()[1:]

    if args:
        try:
            msg_ids = [int(x) for x in args]
        except ValueError:
            return await message.answer("❌ Provide valid integer message IDs.")
        _sessions[uid] = {"mode": "custom", "msg_ids": msg_ids}
        await message.answer(
            f"✅ <b>{len(msg_ids)} IDs captured.</b>\n\nSend /done to generate the link."
        )
    else:
        _sessions[uid] = {"mode": "custom", "msg_ids": []}
        await message.answer(
            "🔢 <b>Custom Batch mode!</b>\n\n"
            "Send DB channel message IDs as space-separated numbers.\n"
            "Example: <code>101 105 112 200</code>\n\n"
            "Send /done when finished or /cancel to abort."
        )


# ── /done ──────────────────────────────────────────────────────────────────────

@router.message(Command("done"), is_admin)
@functools.wraps(lambda m, **kw: None)
async def finish_session(message: Message, bot):
    uid     = message.from_user.id
    session = _sessions.pop(uid, None)

    if session is None:
        return await message.answer("❌ No active session. Start one with /batch or /custom_batch.")

    msg_ids = session["msg_ids"]
    mode    = session["mode"]

    if not msg_ids:
        return await message.answer("❌ No files or IDs collected yet.")

    me = await bot.get_me()

    if mode == "batch":
        param = f"batch_{msg_ids[0]}_{msg_ids[-1]}"
    else:
        param = "cb_" + "_".join(str(i) for i in msg_ids)

    link = f"https://t.me/{me.username}?start={param}"

    await message.answer(
        f"✅ <b>{'Batch' if mode == 'batch' else 'Custom Batch'} link generated!</b>\n\n"
        f"📦 <b>Files:</b> {len(msg_ids)}\n"
        f"🔗 <b>Link:</b> {link}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔗 Share Link", url=link)]]
        ),
        disable_web_page_preview=True,
    )


# ── /cancel ────────────────────────────────────────────────────────────────────

@router.message(Command("cancel"), is_admin)
@functools.wraps(lambda m, **kw: None)
async def cancel_session(message: Message):
    if _sessions.pop(message.from_user.id, None) is not None:
        await message.answer("❌ Session cancelled.")
    else:
        await message.answer("No active session.")


# ── Media collector — during /batch session ────────────────────────────────────

@router.message(is_admin, F.content_type.in_(MEDIA_TYPES))
@functools.wraps(lambda m, **kw: None)
async def collect_batch_file(message: Message):
    uid     = message.from_user.id
    session = _sessions.get(uid)

    if not session or session["mode"] != "batch":
        return  # Not in a batch session

    try:
        stored = await message.copy_to(CHANNEL_ID)
        session["msg_ids"].append(stored.message_id)
        count = len(session["msg_ids"])
        await message.answer(f"✅ File {count} stored. Send more or /done to finish.")
    except Exception as e:
        logger.error(f"Batch store error: {e}")
        await message.answer(f"❌ Failed to store file:\n<code>{e}</code>")


# ── Text ID collector — during /custom_batch session ───────────────────────────

@router.message(is_admin, F.text, ~F.text.startswith("/"))
@functools.wraps(lambda m, **kw: None)
async def collect_custom_ids(message: Message):
    uid     = message.from_user.id
    session = _sessions.get(uid)

    if not session or session["mode"] != "custom":
        return  # Not in a custom_batch session

    valid = [int(p) for p in message.text.split() if p.isdigit()]
    if not valid:
        return await message.answer("❌ No valid IDs. Send space-separated numbers.")

    session["msg_ids"].extend(valid)
    total = len(session["msg_ids"])
    await message.answer(
        f"✅ Added {len(valid)} ID(s). Total: <b>{total}</b>\n\n"
        "Send more or /done to generate the link."
    )
