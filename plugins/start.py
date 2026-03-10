"""
/start — force-sub gate + file delivery.
"""
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction

from config import START_MSG, FORCE_MSG, HELP_TXT, START_PIC, START_PICS, FORCE_PIC, CHANNEL_ID, OWNER
import random
from database.database import CosmicBotz
from helper import user_mention, is_not_banned, full_delivery
from helper.utils import decode_file_id

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
    if FORCE_PIC:
        await message.answer_photo(FORCE_PIC, caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), disable_web_page_preview=True)


def _start_markup():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="ℹ️ Help",  callback_data="help"),
        InlineKeyboardButton(text="👤 About", callback_data="about"),
    ]])

def _pick_pic() -> str:
    """Return a random pic from START_PICS, or fallback to START_PIC."""
    return random.choice(START_PICS) if START_PICS else START_PIC


def _back_btn():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="« Back", callback_data="back_start")
    ]])


def _parse_start_param(start_param: str, fallback_channel: int) -> list[tuple[int, int]]:
    """
    Parse start_param into list of (channel_id, msg_id) tuples.
    Supports:
      <encoded>       — single file, new encoding (channel+msg) or legacy (msg only)
      batch_F_L       — range from F to L in fallback_channel
      cb_E1_E2_...    — each Ei is encoded (channel+msg)
    """
    try:
        if start_param.startswith("batch_"):
            _, s, e = start_param.split("_", 2)
            return [(fallback_channel, mid) for mid in range(int(s), int(e) + 1)]

        if start_param.startswith("cb_"):
            parts  = start_param[3:].split("_")
            result = []
            for p in parts:
                if p.isdigit():
                    # legacy plain msg_id
                    result.append((fallback_channel, int(p)))
                else:
                    ch, mid = decode_file_id(p)
                    result.append((ch, mid))
            return result

        # Single encoded file
        ch, mid = decode_file_id(start_param)
        return [(ch, mid)]
    except Exception as e:
        logger.error(f"_parse_start_param: {e}")
        return []


# ── /start ─────────────────────────────────────────────────────────────────────

@router.message(CommandStart(), is_not_banned)
async def start_handler(message: Message, command: CommandObject, bot):
    # Show action immediately before any processing
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    user = message.from_user
    if not await CosmicBotz.present_user(user.id):
        await CosmicBotz.add_user(user.id)

    start_param   = command.args or ""
    fsub_channels = await _active_fsub_channels(bot)

    if fsub_channels and not await _is_subscribed(bot, user.id, fsub_channels):
        return await _send_fsub_msg(message, fsub_channels, start_param)

    if start_param:
        pairs = _parse_start_param(start_param, CHANNEL_ID)
        if not pairs:
            return await message.answer("❌ Invalid or expired link.")
        await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)  # overrides TYPING
        return await full_delivery(bot, message.chat.id, pairs, start_param)

    mention = user_mention(user)
    text    = START_MSG.replace("{mention}", mention)
    if START_PIC:
        await message.answer_photo(_pick_pic(), caption=text, reply_markup=_start_markup())
    else:
        await message.answer(text, reply_markup=_start_markup())


# ── Reload callback ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("reload"))
async def reload_cb(callback: CallbackQuery, bot):
    user        = callback.from_user
    start_param = callback.data[7:] if len(callback.data) > 6 else ""

    fsub_channels = await _active_fsub_channels(bot)
    if fsub_channels and not await _is_subscribed(bot, user.id, fsub_channels):
        return await callback.answer("❌ You haven't joined all channels!", show_alert=True)

    await callback.message.delete()

    if start_param:
        pairs = _parse_start_param(start_param, CHANNEL_ID)
        if not pairs:
            return await bot.send_message(user.id, "❌ Invalid link.")
        await bot.send_chat_action(user.id, ChatAction.UPLOAD_VIDEO)
        await full_delivery(bot, user.id, pairs, start_param)
    else:
        await bot.send_chat_action(user.id, ChatAction.TYPING)
        mention = user_mention(user)
        text    = START_MSG.replace("{mention}", mention)
        if START_PIC:
            await bot.send_photo(user.id, _pick_pic(), caption=text, reply_markup=_start_markup())
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
async def about_cb(callback: CallbackQuery, bot):
    me   = await bot.get_me()
    text = (
        "<b><blockquote>"
        f"◈ ʙᴏᴛ: {me.full_name}\n"
        f"◈ ᴜꜱᴇʀɴᴀᴍᴇ: @{me.username}\n"
        "◈ ꜰʀᴀᴍᴇᴡᴏʀᴋ: Aiogram 3\n"
        "◈ ʟᴀɴɢᴜᴀɢᴇ: Python 3\n"
        f"◈ ᴅᴇᴠᴇʟᴏᴘᴇʀ: @{OWNER}\n"
        "</blockquote></b>"
    )
    try:
        await callback.message.edit_caption(caption=text, reply_markup=_back_btn())
    except Exception:
        await callback.message.edit_text(text, reply_markup=_back_btn())

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
