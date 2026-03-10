"""
/start — force-sub gate + file delivery.
"""
import asyncio
import functools
import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from config import (
    START_MSG, FORCE_MSG, HELP_TXT, ABOUT_TXT,
    START_PIC, FORCE_PIC, PROTECT_CONTENT,
)
from database.database import CosmicBotz
from helper import (
    user_mention, decode_file_id,
    delete_messages_later, render_caption, is_not_banned,
)

router = Router()
logger = logging.getLogger(__name__)


# ── FSub helpers ───────────────────────────────────────────────────────────────

async def get_active_fsub_channels(bot) -> list:
    """Returns [(ch_id, title, invite_link)] for all mode=on channels."""
    result = []
    for ch_id in await CosmicBotz.show_channels():
        if await CosmicBotz.get_channel_mode(ch_id) != "on":
            continue
        try:
            chat = await bot.get_chat(ch_id)
            link = chat.invite_link or await bot.export_chat_invite_link(ch_id)
            result.append((ch_id, chat.title, link))
        except Exception as e:
            logger.warning(f"FSub channel {ch_id} unavailable: {e}")
    return result


async def user_is_subscribed(bot, user_id: int, channels: list) -> bool:
    for ch_id, _, _ in channels:
        try:
            m = await bot.get_chat_member(ch_id, user_id)
            if m.status in ("left", "kicked", "restricted"):
                return False
        except Exception:
            return False
    return True


async def send_force_sub_msg(message: Message, channels: list, start_param: str = ""):
    mention = user_mention(message.from_user)
    text    = FORCE_MSG.replace("{mention}", mention)
    buttons = [[InlineKeyboardButton(text=f"📢 {t}", url=l)] for _, t, l in channels]
    cb      = f"reload_{start_param}" if start_param else "reload"
    buttons.append([InlineKeyboardButton(text="🔄 Rᴇʟᴏᴀᴅ", callback_data=cb)])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    if FORCE_PIC:
        await message.answer_photo(FORCE_PIC, caption=text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup, disable_web_page_preview=True)


# ── File delivery ──────────────────────────────────────────────────────────────

async def deliver_file(message: Message, bot, start_param: str):
    from config import CHANNEL_ID
    try:
        if start_param.startswith("batch_"):
            _, raw_s, raw_e = start_param.split("_", 2)
            msg_ids = list(range(int(raw_s), int(raw_e) + 1))
        elif start_param.startswith("cb_"):
            msg_ids = [int(x) for x in start_param[3:].split("_") if x.isdigit()]
        else:
            msg_ids = [decode_file_id(start_param)]
    except Exception as e:
        logger.error(f"File ID parse error: {e}")
        return await message.answer("❌ Invalid or expired file link.")

    caption_tpl = await CosmicBotz.get_caption()
    del_timer   = await CosmicBotz.get_del_timer()
    sent_ids    = []

    for msg_id in msg_ids:
        try:
            fwd = await bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=msg_id,
                protect_content=PROTECT_CONTENT,
            )
            if caption_tpl:
                fname = (
                    (fwd.document  and fwd.document.file_name)
                    or (fwd.video  and (fwd.video.file_name or "video.mp4"))
                    or (fwd.audio  and (fwd.audio.file_name or "audio.mp3"))
                    or "file"
                )
                rendered = render_caption(caption_tpl, fname, fwd.caption or "")
                try:
                    await fwd.edit_caption(rendered)
                except Exception:
                    pass
            sent_ids.append(fwd.message_id)
        except Exception as e:
            logger.error(f"copy_message {msg_id}: {e}")

    if del_timer > 0 and sent_ids:
        asyncio.create_task(
            delete_messages_later(bot, message.chat.id, sent_ids, del_timer)
        )
        mins = del_timer // 60
        label = f"{mins} minute(s)" if mins else f"{del_timer} second(s)"
        notice = await message.answer(
            f"⚠️ <b>Files will auto-delete in {label}.</b> Please save them before then."
        )
        asyncio.create_task(
            delete_messages_later(bot, message.chat.id, [notice.message_id], del_timer)
        )


# ── /start ─────────────────────────────────────────────────────────────────────

@router.message(CommandStart(), is_not_banned)
@functools.wraps(lambda m, **kw: None)
async def start_handler(message: Message, command: CommandObject, bot):
    user = message.from_user
    if not await CosmicBotz.present_user(user.id):
        await CosmicBotz.add_user(user.id)

    start_param   = command.args or ""
    fsub_channels = await get_active_fsub_channels(bot)

    if fsub_channels and not await user_is_subscribed(bot, user.id, fsub_channels):
        return await send_force_sub_msg(message, fsub_channels, start_param)

    if start_param:
        return await deliver_file(message, bot, start_param)

    mention = user_mention(user)
    text    = START_MSG.replace("{mention}", mention)
    markup  = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="ℹ️ Help",  callback_data="help"),
        InlineKeyboardButton(text="👤 About", callback_data="about"),
    ]])
    if START_PIC:
        await message.answer_photo(START_PIC, caption=text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


# ── Reload callback ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("reload"))
@functools.wraps(lambda c, **kw: None)
async def reload_callback(callback: CallbackQuery, bot):
    user        = callback.from_user
    # data is "reload" or "reload_<start_param>"
    start_param = callback.data[7:] if len(callback.data) > 6 else ""

    fsub_channels = await get_active_fsub_channels(bot)
    if fsub_channels and not await user_is_subscribed(bot, user.id, fsub_channels):
        return await callback.answer(
            "❌ You haven't joined all required channels!", show_alert=True
        )

    await callback.message.delete()

    if start_param:
        await deliver_file(callback.message, bot, start_param)
    else:
        mention = user_mention(user)
        text    = START_MSG.replace("{mention}", mention)
        markup  = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="ℹ️ Help",  callback_data="help"),
            InlineKeyboardButton(text="👤 About", callback_data="about"),
        ]])
        if START_PIC:
            await bot.send_photo(user.id, photo=START_PIC, caption=text, reply_markup=markup)
        else:
            await bot.send_message(user.id, text, reply_markup=markup)


# ── Help / About / Back / Close ────────────────────────────────────────────────

def _back_btn():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Back", callback_data="back_start")]
    ])

def _start_markup():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="ℹ️ Help",  callback_data="help"),
        InlineKeyboardButton(text="👤 About", callback_data="about"),
    ]])


@router.callback_query(F.data == "help")
@functools.wraps(lambda c, **kw: None)
async def help_cb(callback: CallbackQuery):
    try:
        await callback.message.edit_caption(caption=HELP_TXT, reply_markup=_back_btn())
    except Exception:
        await callback.message.edit_text(HELP_TXT, reply_markup=_back_btn())


@router.callback_query(F.data == "about")
@functools.wraps(lambda c, **kw: None)
async def about_cb(callback: CallbackQuery):
    try:
        await callback.message.edit_caption(caption=ABOUT_TXT, reply_markup=_back_btn())
    except Exception:
        await callback.message.edit_text(ABOUT_TXT, reply_markup=_back_btn())


@router.callback_query(F.data == "back_start")
@functools.wraps(lambda c, **kw: None)
async def back_start_cb(callback: CallbackQuery):
    mention = user_mention(callback.from_user)
    text    = START_MSG.replace("{mention}", mention)
    try:
        await callback.message.edit_caption(caption=text, reply_markup=_start_markup())
    except Exception:
        await callback.message.edit_text(text, reply_markup=_start_markup())


@router.callback_query(F.data == "close")
@functools.wraps(lambda c, **kw: None)
async def close_cb(callback: CallbackQuery):
    await callback.message.delete()
