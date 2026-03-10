"""
/genlink  — reply to file → store in DB channel → get shareable link
Auto-link — send any media in private DM → instant link (no command needed)
Both log the file to the log channel if set.
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ContentType

from config import CHANNEL_ID
from database.database import CosmicBotz
from helper import is_admin, encode_file_id

router = Router()
logger = logging.getLogger(__name__)

MEDIA_TYPES = {
    ContentType.DOCUMENT, ContentType.VIDEO, ContentType.AUDIO,
    ContentType.PHOTO, ContentType.ANIMATION, ContentType.VOICE, ContentType.VIDEO_NOTE,
}


async def _store_and_link(message: Message, bot, source_msg: Message) -> tuple[str, int] | None:
    """Copy source_msg to DB channel, return (link, msg_id)."""
    try:
        stored = await source_msg.copy_to(CHANNEL_ID)
        msg_id = stored.message_id
    except Exception as e:
        logger.error(f"store_and_link: {e}")
        await message.answer(f"❌ Failed to store:\n<code>{e}</code>")
        return None

    encoded = encode_file_id(msg_id)
    me      = await bot.get_me()
    link    = f"https://t.me/{me.username}?start={encoded}"
    return link, msg_id


async def _log_to_channel(bot, link: str, source_msg: Message):
    """Forward the file + link to the log channel."""
    log_ch = await CosmicBotz.get_log_channel()
    if not log_ch:
        return
    try:
        await source_msg.copy_to(log_ch)
        await bot.send_message(
            log_ch,
            f"🔗 <b>New link generated</b>\n{link}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Share Link", url=link)]
            ]),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.warning(f"log_to_channel: {e}")


def _link_markup(link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Share Link", url=link)]
    ])


# ── /genlink ───────────────────────────────────────────────────────────────────

@router.message(Command("genlink"), is_admin)
async def genlink_cmd(message: Message, bot):
    reply = message.reply_to_message
    if not reply:
        return await message.answer(
            "❌ Reply to any file with <code>/genlink</code> to generate a link."
        )
    has_media = any(getattr(reply, mt.value, None) for mt in MEDIA_TYPES)
    if not has_media:
        return await message.answer("❌ Reply to a media file.")

    wait   = await message.answer("⏳ Storing...")
    result = await _store_and_link(message, bot, reply)
    if not result:
        return

    link, msg_id = result
    await wait.edit_text(
        f"✅ <b>Link generated!</b>\n\n"
        f"🔗 <b>Link:</b> {link}\n"
        f"📁 <b>DB Msg ID:</b> <code>{msg_id}</code>",
        reply_markup=_link_markup(link),
        disable_web_page_preview=True,
    )
    await _log_to_channel(bot, link, reply)


# ── Auto genlink — private DM, admin, no active session ────────────────────────

@router.message(
    is_admin,
    F.chat.type == "private",
    F.content_type.in_(MEDIA_TYPES),
)
async def auto_genlink(message: Message, bot):
    # Only fire when NOT in an active batch/pro session
    from plugins.batch import _sessions, _batch_wizard
    uid = message.from_user.id
    if uid in _sessions or uid in _batch_wizard:
        return  # batch.py will handle it

    wait   = await message.answer("⏳ Storing and generating link...")
    result = await _store_and_link(message, bot, message)
    if not result:
        return

    link, msg_id = result
    await wait.edit_text(
        f"✅ <b>Link generated!</b>\n\n"
        f"🔗 {link}\n"
        f"📁 DB Msg ID: <code>{msg_id}</code>",
        reply_markup=_link_markup(link),
        disable_web_page_preview=True,
    )
    await _log_to_channel(bot, link, message)
