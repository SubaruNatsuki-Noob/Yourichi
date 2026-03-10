"""
/start — force-sub gate + file delivery.
"""
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import START_MSG, FORCE_MSG, HELP_TXT, ABOUT_TXT, START_PIC, FORCE_PIC
from database.database import CosmicBotz
from helper import user_mention, decode_file_id, is_not_banned, full_delivery

router = Router()
logger = logging.getLogger(__name__)


async def _active_fsub_channels(bot) -> list:
    result = []
    for ch_id in await CosmicBotz.show_channels():
        if await CosmicBotz.get_channel_mode(ch_id) != "on":
            continue
        try:
            chat = await bot.get_chat(ch_id)
            link = chat.invite_link or await bot.export_chat_invite_link(ch_id)
            result.append((ch_id, chat.title, link))
        except Exception as e:
            logger.warning(f"FSub {ch_id}: {e}")
    return result


async def _is_subscribed(bot, uid: int, channels: list) -> bool:
    for ch_id, _, _ in channels:
        try:
            m = await bot.get_chat_member(ch_id, uid)
            if m.status in ("left", "kicked", "restricted"):
                return False
        except Exception:
            return False
    return True


async def _send_fsub_msg(message: Message, channels: list, start_param: str = ""):
    mention = user_mention(message.from_user)
    text    = FORCE_MSG.replace("{mention}", mention)
    buttons = [[InlineKeyboardButton(text=f"📢 {t}", url=l)] for _, t, l in channels]
    cb      = f"reload_{start_param}" if start_param else "reload"
    buttons.append([InlineKeyboardButton(text="🔄 Reload", callback_data=cb)])
    markup  = InlineKeyboardMarkup(inline_keyboard=buttons)
    if FORCE_PIC:
        await message.answer_photo(FORCE_PIC, caption=text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup, disable_web_page_preview=True)


def _start_markup():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="ℹ️ Help",  callback_data="help"),
        InlineKeyboardButton(text="👤 About", callback_data="about"),
    ]])

def _back_btn():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="« Back", callback_data="back_start")
    ]])


# ── /start ─────────────────────────────────────────────────────────────────────

@router.message(CommandStart(), is_not_banned)
async def start_handler(message: Message, command: CommandObject, bot):
    user = message.from_user
    if not await CosmicBotz.present_user(user.id):
        await CosmicBotz.add_user(user.id)

    start_param   = command.args or ""
    fsub_channels = await _active_fsub_channels(bot)

    if fsub_channels and not await _is_subscribed(bot, user.id, fsub_channels):
        return await _send_fsub_msg(message, fsub_channels, start_param)

    if start_param:
        try:
            if start_param.startswith("batch_"):
                _, s, e = start_param.split("_", 2)
                msg_ids = list(range(int(s), int(e) + 1))
            elif start_param.startswith("cb_"):
                msg_ids = [int(x) for x in start_param[3:].split("_") if x.isdigit()]
            else:
                msg_ids = [decode_file_id(start_param)]
        except Exception as ex:
            logger.error(f"start param parse: {ex}")
            return await message.answer("❌ Invalid or expired link.")
        return await full_delivery(bot, message.chat.id, msg_ids, start_param)

    mention = user_mention(user)
    text    = START_MSG.replace("{mention}", mention)
    if START_PIC:
        await message.answer_photo(START_PIC, caption=text, reply_markup=_start_markup())
    else:
        await message.answer(text, reply_markup=_start_markup())


# ── Reload ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("reload"))
async def reload_cb(callback: CallbackQuery, bot):
    user        = callback.from_user
    start_param = callback.data[7:] if len(callback.data) > 6 else ""

    fsub_channels = await _active_fsub_channels(bot)
    if fsub_channels and not await _is_subscribed(bot, user.id, fsub_channels):
        return await callback.answer("❌ You haven't joined all channels!", show_alert=True)

    await callback.message.delete()

    if start_param:
        try:
            if start_param.startswith("batch_"):
                _, s, e = start_param.split("_", 2)
                msg_ids = list(range(int(s), int(e) + 1))
            elif start_param.startswith("cb_"):
                msg_ids = [int(x) for x in start_param[3:].split("_") if x.isdigit()]
            else:
                msg_ids = [decode_file_id(start_param)]
        except Exception:
            return await bot.send_message(user.id, "❌ Invalid link.")
        await full_delivery(bot, user.id, msg_ids, start_param)
    else:
        mention = user_mention(user)
        text    = START_MSG.replace("{mention}", mention)
        if START_PIC:
            await bot.send_photo(user.id, START_PIC, caption=text, reply_markup=_start_markup())
        else:
            await bot.send_message(user.id, text, reply_markup=_start_markup())


# ── Help / About / Back / Close ────────────────────────────────────────────────

@router.callback_query(F.data == "help")
async def help_cb(callback: CallbackQuery):
    try:
        await callback.message.edit_caption(caption=HELP_TXT, reply_markup=_back_btn())
    except Exception:
        await callback.message.edit_text(HELP_TXT, reply_markup=_back_btn())

@router.callback_query(F.data == "about")
async def about_cb(callback: CallbackQuery):
    try:
        await callback.message.edit_caption(caption=ABOUT_TXT, reply_markup=_back_btn())
    except Exception:
        await callback.message.edit_text(ABOUT_TXT, reply_markup=_back_btn())

@router.callback_query(F.data == "back_start")
async def back_start_cb(callback: CallbackQuery):
    mention = user_mention(callback.from_user)
    text    = START_MSG.replace("{mention}", mention)
    try:
        await callback.message.edit_caption(caption=text, reply_markup=_start_markup())
    except Exception:
        await callback.message.edit_text(text, reply_markup=_start_markup())

@router.callback_query(F.data == "close")
async def close_cb(callback: CallbackQuery):
    await callback.message.delete()
