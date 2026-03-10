"""
/genlink  — reply to file → store in DB channel with caption → shareable link
Auto-link — send any media in private DM (no session) → same
Log channel support.
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ContentType

from config import CHANNEL_ID
from database.database import CosmicBotz
from helper import is_admin, encode_file_id
from helper.delivery import store_file_with_caption

router = Router()
logger = logging.getLogger(__name__)

MEDIA_TYPES = {
    ContentType.DOCUMENT, ContentType.VIDEO, ContentType.AUDIO,
    ContentType.PHOTO, ContentType.ANIMATION, ContentType.VOICE, ContentType.VIDEO_NOTE,
}


async def _make_link(bot, msg_id: int) -> str:
    me      = await bot.get_me()
    encoded = encode_file_id(CHANNEL_ID, msg_id)
    return f"https://t.me/{me.username}?start={encoded}"


def _markup(link: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Share Link", url=link)]
    ])


async def _log(bot, link: str, source_msg: Message):
    log_ch = await CosmicBotz.get_log_channel()
    if not log_ch:
        return
    try:
        await source_msg.copy_to(log_ch)
        await bot.send_message(
            log_ch, f"🔗 <b>New link</b>\n{link}",
            reply_markup=_markup(link),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.warning(f"_log: {e}")


# ── /genlink ───────────────────────────────────────────────────────────────────

@router.message(Command("genlink"), is_admin)
async def genlink_cmd(message: Message, bot):
    reply = message.reply_to_message
    if not reply:
        return await message.answer("❌ Reply to any file with <code>/genlink</code>.")

    has_media = any(getattr(reply, mt.value, None) for mt in MEDIA_TYPES)
    if not has_media:
        return await message.answer("❌ Reply to a media file.")

    wait   = await message.answer("⏳ Storing...")
    msg_id = await store_file_with_caption(bot, reply)
    if not msg_id:
        return await wait.edit_text("❌ Failed to store file.")

    link = await _make_link(bot, msg_id)
    await wait.edit_text(
        f"✅ <b>Link generated!</b>\n\n🔗 {link}\n📁 DB Msg ID: <code>{msg_id}</code>",
        reply_markup=_markup(link),
        disable_web_page_preview=True,
    )
    await _log(bot, link, reply)


# ── Auto genlink — private DM, no active session ───────────────────────────────

@router.message(is_admin, F.chat.type == "private", F.content_type.in_(MEDIA_TYPES))
async def auto_genlink(message: Message, bot):
    from plugins.batch import _sessions, _batch_wizard, _pro_wizard
    uid = message.from_user.id
    if uid in _sessions or uid in _batch_wizard or uid in _pro_wizard:
        return  # batch.py handles it

    wait   = await message.answer("⏳ Storing and generating link...")
    msg_id = await store_file_with_caption(bot, message)
    if not msg_id:
        return await wait.edit_text("❌ Failed to store.")

    link = await _make_link(bot, msg_id)
    await wait.edit_text(
        f"✅ <b>Link generated!</b>\n\n🔗 {link}\n📁 DB Msg ID: <code>{msg_id}</code>",
        reply_markup=_markup(link),
        disable_web_page_preview=True,
    )
    await _log(bot, link, message)
