"""
Core delivery engine.
Caption baked at store time. Tasks held in _tasks set to prevent GC cancellation.
"""
import asyncio
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import CHANNEL_ID, PROTECT_CONTENT
from database.database import CosmicBotz
from helper.caption_parser import render_caption

logger = logging.getLogger(__name__)

# Strong reference set — prevents asyncio from GC-cancelling tasks before they run
_tasks: set = set()


def _extract_fname(msg) -> str:
    return (
        (msg.document   and msg.document.file_name)
        or (msg.video   and (msg.video.file_name   or "video.mp4"))
        or (msg.audio   and (msg.audio.file_name   or "audio.mp3"))
        or (msg.voice   and "voice.ogg")
        or (msg.animation and "animation.gif")
        or (msg.photo   and "photo.jpg")
        or "file"
    )


async def store_file_with_caption(bot: Bot, source_msg, channel_id: int = CHANNEL_ID) -> int | None:
    try:
        stored = await source_msg.copy_to(channel_id)
        msg_id = stored.message_id
    except Exception as e:
        logger.error(f"store_file_with_caption: {e}")
        return None

    caption_tpl = await CosmicBotz.get_caption()
    if caption_tpl:
        fname    = _extract_fname(source_msg)
        rendered = render_caption(caption_tpl, fname)
        try:
            await bot.edit_message_caption(
                chat_id=channel_id, message_id=msg_id, caption=rendered,
            )
        except Exception as e:
            logger.debug(f"store caption edit msg={msg_id}: {e}")

    return msg_id


async def apply_caption_in_db(bot: Bot, msg_id: int, channel_id: int = CHANNEL_ID):
    caption_tpl = await CosmicBotz.get_caption()
    if not caption_tpl:
        return
    try:
        peek = await bot.forward_message(
            chat_id=channel_id, from_chat_id=channel_id, message_id=msg_id,
        )
        fname = _extract_fname(peek)
        try:
            await bot.delete_message(channel_id, peek.message_id)
        except Exception:
            pass
        rendered = render_caption(caption_tpl, fname)
        await bot.edit_message_caption(
            chat_id=channel_id, message_id=msg_id, caption=rendered,
        )
    except Exception as e:
        logger.debug(f"apply_caption_in_db msg={msg_id}: {e}")


async def _send_wrapper(bot: Bot, chat_id: int, data: dict) -> int | None:
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


async def _autodelete_task(
    bot: Bot,
    chat_id: int,
    file_msg_ids: list,
    notice_msg_id: int,
    delay: int,
    reget_link: str,
    label: str,
):
    await asyncio.sleep(delay)

    for mid in file_msg_ids:
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=notice_msg_id,
            text=(
                f"🗑 ꜰɪʟᴇꜱ ᴅᴇʟᴇᴛᴇᴅ\n\n"
                f"ɢᴇᴛ ᴛʜᴇᴍ ᴀɢᴀɪɴ ᴀɴʏᴛɪᴍᴇ ʙᴇʟᴏᴡ ↓"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 ɢᴇᴛ ꜰɪʟᴇꜱ ᴀɢᴀɪɴ", url=reget_link)]
            ]),
        )
    except Exception as e:
        logger.debug(f"edit notice failed: {e}")


async def full_delivery(
    bot: Bot,
    chat_id: int,
    pairs: list[tuple[int, int]],
    start_param: str,
    apply_caption: bool = True,
):
    del_timer = await CosmicBotz.get_del_timer()
    all_sent  = []

    start_data = await CosmicBotz.get_batch_start()
    if start_data:
        mid = await _send_wrapper(bot, chat_id, start_data)
        if mid:
            all_sent.append(mid)

    for channel_id, msg_id in pairs:
        if apply_caption:
            await apply_caption_in_db(bot, msg_id, channel_id)
        try:
            result = await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=channel_id,
                message_id=msg_id,
                protect_content=PROTECT_CONTENT,
            )
            all_sent.append(result.message_id)
        except Exception as e:
            logger.error(f"copy_message ch={channel_id} msg={msg_id}: {e}")

    end_data = await CosmicBotz.get_batch_end()
    if end_data:
        mid = await _send_wrapper(bot, chat_id, end_data)
        if mid:
            all_sent.append(mid)

    if del_timer > 0 and all_sent:
        me    = await bot.get_me()
        link  = f"https://t.me/{me.username}?start={start_param}"
        mins  = del_timer // 60
        label = f"{mins}ᴍ" if mins else f"{del_timer}ꜱ"

        notice = await bot.send_message(
            chat_id,
            f"⚠️ ꜰɪʟᴇꜱ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ɪɴ {label}\n\nꜱᴀᴠᴇ ᴛʜᴇᴍ ɴᴏᴡ ↓",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"⏳ {label} ʟᴇꜰᴛ", callback_data="noop")]
            ])
        )

        # Hold strong reference so task isn't GC'd before it fires
        task = asyncio.create_task(
            _autodelete_task(
                bot, chat_id, all_sent, notice.message_id,
                del_timer, link, label,
            )
        )
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
