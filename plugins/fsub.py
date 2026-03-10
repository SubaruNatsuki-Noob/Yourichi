"""
Force-subscribe management.
Commands: addchnl, delchnl, listchnl, fsub_mode, delreq
Events:   chat_join_request, chat_member (leave tracking)
"""
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    ChatJoinRequest, ChatMemberUpdated,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from database.database import CosmicBotz
from helper import is_admin

router = Router()
logger = logging.getLogger(__name__)


# ── /addchnl ───────────────────────────────────────────────────────────────────

@router.message(Command("addchnl"), is_admin)
async def addchnl_cmd(message: Message, bot):
    temp = await message.answer("<i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i>")
    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        return await temp.edit_text("Usage: <code>/addchnl -100xxxxxxxxxx</code>")
    try:
        chat_id = int(args[1])
    except ValueError:
        return await temp.edit_text("❌ Invalid chat ID.")

    if chat_id in await CosmicBotz.show_channels():
        return await temp.edit_text(f"⚠️ Already added: <code>{chat_id}</code>")

    try:
        chat      = await bot.get_chat(chat_id)
        bot_me    = await bot.get_me()
        bot_mbr   = await bot.get_chat_member(chat_id, bot_me.id)

        if chat.type not in ("channel", "supergroup"):
            return await temp.edit_text("❌ Only channels or supergroups allowed.")
        if bot_mbr.status not in ("administrator", "creator"):
            return await temp.edit_text("❌ Bot must be admin in that chat.")

        try:
            link = chat.invite_link or await bot.export_chat_invite_link(chat_id)
        except Exception:
            link = f"https://t.me/{chat.username}" if chat.username else str(chat_id)

        await CosmicBotz.add_channel(chat_id)
        await temp.edit_text(
            f"✅ <b>Added!</b>\n\n"
            f"<b>Name:</b> <a href='{link}'>{chat.title}</a>\n"
            f"<b>ID:</b> <code>{chat_id}</code>",
            disable_web_page_preview=True,
        )
    except Exception as e:
        await temp.edit_text(f"❌ Failed:\n<code>{e}</code>")


# ── /delchnl ───────────────────────────────────────────────────────────────────

@router.message(Command("delchnl"), is_admin)
async def delchnl_cmd(message: Message):
    temp         = await message.answer("<i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i>")
    args         = message.text.split(maxsplit=1)
    all_channels = await CosmicBotz.show_channels()

    if len(args) != 2:
        return await temp.edit_text(
            "Usage: <code>/delchnl &lt;channel_id | all&gt;</code>"
        )

    if args[1].lower() == "all":
        if not all_channels:
            return await temp.edit_text("❌ No force-sub channels found.")
        for ch in all_channels:
            await CosmicBotz.rem_channel(ch)
        return await temp.edit_text("✅ All force-sub channels removed.")

    try:
        ch_id = int(args[1])
    except ValueError:
        return await temp.edit_text("❌ Invalid channel ID.")

    if ch_id in all_channels:
        await CosmicBotz.rem_channel(ch_id)
        await temp.edit_text(f"✅ Removed: <code>{ch_id}</code>")
    else:
        await temp.edit_text(f"❌ Not found: <code>{ch_id}</code>")


# ── /listchnl ──────────────────────────────────────────────────────────────────

@router.message(Command("listchnl"), is_admin)
async def listchnl_cmd(message: Message, bot):
    temp     = await message.answer("<i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i>")
    channels = await CosmicBotz.show_channels()

    if not channels:
        return await temp.edit_text("❌ No force-sub channels found.")

    result = "<b>⚡ Force-sub Channels:</b>\n\n"
    for ch_id in channels:
        mode   = await CosmicBotz.get_channel_mode(ch_id)
        status = "🟢" if mode == "on" else "🔴"
        try:
            chat = await bot.get_chat(ch_id)
            link = chat.invite_link or await bot.export_chat_invite_link(ch_id)
            result += f"{status} <a href='{link}'>{chat.title}</a> [<code>{ch_id}</code>]\n"
        except Exception:
            result += f"{status} <code>{ch_id}</code> — <i>Unavailable</i>\n"

    await temp.edit_text(
        result,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Close ✖️", callback_data="close")]]
        ),
    )


# ── /fsub_mode ─────────────────────────────────────────────────────────────────

@router.message(Command("fsub_mode"), is_admin)
async def fsub_mode_cmd(message: Message, bot):
    temp     = await message.answer("<i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i>")
    channels = await CosmicBotz.show_channels()

    if not channels:
        return await temp.edit_text("❌ No force-sub channels found.")

    async def build_markup():
        buttons = []
        for ch_id in channels:
            mode   = await CosmicBotz.get_channel_mode(ch_id)
            status = "🟢" if mode == "on" else "🔴"
            try:
                chat  = await bot.get_chat(ch_id)
                title = f"{status} {chat.title}"
            except Exception:
                title = f"{status} {ch_id}"
            buttons.append([InlineKeyboardButton(text=title, callback_data=f"rfs_{ch_id}")])
        buttons.append([InlineKeyboardButton(text="Close ✖️", callback_data="close")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    await temp.edit_text(
        "<b>⚡ Select a channel to toggle Force-Sub:</b>",
        reply_markup=await build_markup(),
    )


@router.callback_query(F.data.startswith("rfs_"), is_admin)
async def toggle_fsub_cb(callback: CallbackQuery, bot):
    ch_id   = int(callback.data.split("_", 1)[1])
    current = await CosmicBotz.get_channel_mode(ch_id)
    new     = "off" if current == "on" else "on"
    await CosmicBotz.set_channel_mode(ch_id, new)

    channels = await CosmicBotz.show_channels()
    buttons  = []
    for cid in channels:
        mode   = await CosmicBotz.get_channel_mode(cid)
        status = "🟢" if mode == "on" else "🔴"
        try:
            chat  = await bot.get_chat(cid)
            title = f"{status} {chat.title}"
        except Exception:
            title = f"{status} {cid}"
        buttons.append([InlineKeyboardButton(text=title, callback_data=f"rfs_{cid}")])
    buttons.append([InlineKeyboardButton(text="Close ✖️", callback_data="close")])

    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    lbl = "✅ Enabled" if new == "on" else "🔴 Disabled"
    await callback.answer(f"{lbl} for {ch_id}")


# ── /delreq ────────────────────────────────────────────────────────────────────

@router.message(Command("delreq"), is_admin)
async def delreq_cmd(message: Message, bot):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Usage: <code>/delreq &lt;channel_id&gt;</code>")
    try:
        channel_id = int(args[1])
    except ValueError:
        return await message.answer("❌ Invalid channel ID.")

    channel_data = await CosmicBotz.req_fsub_col().find_one({"_id": channel_id})
    if not channel_data:
        return await message.answer("ℹ️ No request data found for this channel.")

    user_ids = channel_data.get("user_ids", [])
    if not user_ids:
        return await message.answer("✅ No users to process.")

    removed, skipped = 0, 0
    for uid in user_ids:
        try:
            member = await bot.get_chat_member(channel_id, uid)
            if member.status in ("member", "administrator", "creator"):
                skipped += 1
            else:
                await CosmicBotz.del_req_user(channel_id, uid)
                removed += 1
        except Exception:
            await CosmicBotz.del_req_user(channel_id, uid)
            removed += 1

    await message.answer(
        f"✅ <b>Cleanup done for</b> <code>{channel_id}</code>\n\n"
        f"🗑️ Removed (not in channel): <code>{removed}</code>\n"
        f"✅ Still members (kept): <code>{skipped}</code>"
    )


# ── Chat join request tracking ──────────────────────────────────────────────────

@router.chat_join_request()
async def on_join_request(request: ChatJoinRequest):
    if await CosmicBotz.reqChannel_exist(request.chat.id):
        if not await CosmicBotz.req_user_exist(request.chat.id, request.from_user.id):
            await CosmicBotz.req_user(request.chat.id, request.from_user.id)


# ── Member leave tracking ───────────────────────────────────────────────────────

@router.chat_member()
async def on_chat_member(update: ChatMemberUpdated):
    if not await CosmicBotz.reqChannel_exist(update.chat.id):
        return
    old = update.old_chat_member
    new = update.new_chat_member
    # User left or was kicked
    if old and old.status in ("member", "administrator", "creator") and new.status in ("left", "kicked"):
        if await CosmicBotz.req_user_exist(update.chat.id, old.user.id):
            await CosmicBotz.del_req_user(update.chat.id, old.user.id)
