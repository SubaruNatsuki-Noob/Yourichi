"""
/genlink — reply to any file → store it in DB channel → get a shareable link.
"""
import functools
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import CHANNEL_ID
from database.database import CosmicBotz
from helper import is_admin, encode_file_id

router  = Router()
logger  = logging.getLogger(__name__)

MEDIA_TYPES = {"document", "video", "audio", "photo", "animation", "voice", "video_note"}


@router.message(Command("genlink"), is_admin)
@functools.wraps(lambda m, **kw: None)
async def genlink_cmd(message: Message, bot):
    reply = message.reply_to_message

    if not reply:
        return await message.answer(
            "❌ <b>Usage:</b>\n\n"
            "Reply to any file with <code>/genlink</code> and I'll store it "
            "and generate a shareable link instantly."
        )

    has_media = any(getattr(reply, mt, None) for mt in MEDIA_TYPES)
    if not has_media:
        return await message.answer("❌ Reply to a file (document, video, audio, photo, etc.)")

    wait = await message.answer("⏳ Storing and generating link...")

    try:
        stored = await reply.copy_to(CHANNEL_ID)
        msg_id = stored.message_id
    except Exception as e:
        logger.error(f"/genlink store error: {e}")
        return await wait.edit_text(f"❌ Failed to store file:\n<code>{e}</code>")

    encoded = encode_file_id(msg_id)
    me      = await bot.get_me()
    link    = f"https://t.me/{me.username}?start={encoded}"

    await wait.edit_text(
        f"✅ <b>Link generated!</b>\n\n"
        f"🔗 <b>Link:</b> {link}\n"
        f"📁 <b>Msg ID:</b> <code>{msg_id}</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔗 Share", url=link)]]
        ),
        disable_web_page_preview=True,
    )
