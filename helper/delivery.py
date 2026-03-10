"""
Core delivery engine — used by all file-sending features.
Handles: start msg, files with caption, end msg, auto-delete + re-request button.
"""
import asyncio
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import CHANNEL_ID, PROTECT_CONTENT
from database.database import CosmicBotz
from helper.caption_parser import render_caption

logger = logging.getLogger(__name__)


async def _send_wrapper(bot: Bot, chat_id: int, data: dict) -> int | None:
    """Send a start/end wrapper message. Returns message_id."""
    if not data:
        return None
    try:
        if data["type"] == "text":
            m = await bot.send_message(chat_id, data["content"])
        elif data["type"] == "photo":
            m = await bot.send_photo(chat_id, data["file_id"], caption=data.get("caption", ""))
        elif data["type"] == "video":
            m = await bot.send_video(chat_id, data["file_id"], caption=data.get("caption", ""))
        else:
            return None
        return m.message_id
    except Exception as e:
        logger.error(f"_send_wrapper: {e}")
        return None


async def _copy_with_caption(bot: Bot, chat_id: int, msg_id: int, caption_tpl: str) -> int | None:
    """Copy one file from DB channel to user, applying caption template."""
    try:
        fwd = await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=CHANNEL_ID,
            message_id=msg_id,
            protect_content=PROTECT_CONTENT,
        )
        if caption_tpl:
            # Extract filename from the message object
            fname = (
                (fwd.document  and fwd.document.file_name)
                or (fwd.video  and (fwd.video.file_name   or "video.mp4"))
                or (fwd.audio  and (fwd.audio.file_name   or "audio.mp3"))
                or (fwd.voice  and "voice.ogg")
                or (fwd.animation and "animation.gif")
                or "file"
            )
            rendered = render_caption(caption_tpl, fname)
            try:
                await bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=fwd.message_id,
                    caption=rendered,
                )
            except Exception:
                pass  # some media types don't support captions
        return fwd.message_id
    except Exception as e:
        logger.error(f"_copy_with_caption msg_id={msg_id}: {e}")
        return None


async def _autodelete_task(bot: Bot, chat_id: int, msg_ids: list, delay: int, reget_link: str):
    await asyncio.sleep(delay)
    for mid in msg_ids:
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass
    try:
        await bot.send_message(
            chat_id,
            "🗑 <b>Your files have been deleted.</b>\n\nTap below to get them again anytime:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Get Files Again", url=reget_link)]
            ])
        )
    except Exception:
        pass


async def full_delivery(bot: Bot, chat_id: int, msg_ids: list[int], start_param: str):
    """
    Full delivery pipeline:
      1. Start wrapper message
      2. All files (with caption applied)
      3. End wrapper message
      4. Auto-delete notice + schedule deletion
    """
    caption_tpl = await CosmicBotz.get_caption() or ""
    del_timer   = await CosmicBotz.get_del_timer()
    all_sent    = []

    # 1. Start message
    start_data = await CosmicBotz.get_batch_start()
    if start_data:
        mid = await _send_wrapper(bot, chat_id, start_data)
        if mid:
            all_sent.append(mid)

    # 2. Files
    for msg_id in msg_ids:
        mid = await _copy_with_caption(bot, chat_id, msg_id, caption_tpl)
        if mid:
            all_sent.append(mid)

    # 3. End message
    end_data = await CosmicBotz.get_batch_end()
    if end_data:
        mid = await _send_wrapper(bot, chat_id, end_data)
        if mid:
            all_sent.append(mid)

    # 4. Auto-delete
    if del_timer > 0 and all_sent:
        me    = await bot.get_me()
        link  = f"https://t.me/{me.username}?start={start_param}"
        mins  = del_timer // 60
        label = f"{mins} minute(s)" if mins else f"{del_timer} second(s)"
        notice = await bot.send_message(
            chat_id,
            f"⚠️ <b>Files will auto-delete in {label}.</b> Save them now."
        )
        all_sent.append(notice.message_id)
        asyncio.create_task(
            _autodelete_task(bot, chat_id, all_sent, del_timer, link)
        )
