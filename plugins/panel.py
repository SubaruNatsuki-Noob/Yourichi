"""
Admin Panel — full inline control for all settings.
/panel
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database.database import CosmicBotz
from helper import is_admin, is_owner, human_readable_time
from config import OWNER_ID

router   = Router()
logger   = logging.getLogger(__name__)
_waiting = {}  # uid -> action string


def B(text, data): return InlineKeyboardButton(text=text, callback_data=data)
def KB(*rows):     return InlineKeyboardMarkup(inline_keyboard=list(rows))


# ── Panel screens ──────────────────────────────────────────────────────────────

async def main_panel():
    return "⚙️ <b>Admin Panel</b>\n\nSelect a section:", KB(
        [B("⏱ Auto Delete",  "pn_autodel"),  B("💬 Caption",    "pn_caption")],
        [B("📢 Force Sub",    "pn_fsub"),     B("📦 Batch Msgs", "pn_batchmsg")],
        [B("👮 Admins",       "pn_admins"),   B("🚫 Banned",     "pn_banned")],
        [B("📋 Log Channel",  "pn_log"),      B("📊 Stats",      "pn_stats")],
        [B("❌ Close",        "pn_close")],
    )


async def autodel_panel():
    secs  = await CosmicBotz.get_del_timer()
    label = human_readable_time(secs) if secs else "Disabled"
    return (
        f"⏱ <b>Auto Delete</b>\n\nCurrent: <b>{label}</b>\n\n"
        f"Pick a preset or send a custom value in seconds:",
        KB(
            [B("5 min",  "ad_300"),  B("10 min", "ad_600"),  B("15 min", "ad_900")],
            [B("30 min", "ad_1800"), B("1 hour", "ad_3600"), B("2 hours","ad_7200")],
            [B("❌ Disable","ad_0"), B("✏️ Custom","ad_custom")],
            [B("« Back", "pn_main")],
        )
    )


async def caption_panel():
    tpl    = await CosmicBotz.get_caption()
    status = f"<code>{tpl}</code>" if tpl else "<i>Not set (original captions used)</i>"
    return (
        f"💬 <b>Caption Template</b>\n\nCurrent:\n{status}\n\n"
        f"<b>Variables:</b> <code>{{title}}</code> <code>{{clean_title}}</code> "
        f"<code>{{episode}}</code> <code>{{season}}</code> <code>{{quality}}</code> <code>{{extension}}</code>",
        KB(
            [B("✏️ Set Caption", "cap_set"), B("🗑 Clear", "cap_clear")],
            [B("« Back", "pn_main")],
        )
    )


async def fsub_panel(bot):
    channels = await CosmicBotz.show_channels()
    lines    = []
    rows     = []
    for ch_id in channels:
        mode = await CosmicBotz.get_channel_mode(ch_id)
        icon = "🟢" if mode == "on" else "🔴"
        try:
            chat  = await bot.get_chat(ch_id)
            title = chat.title[:20]
        except Exception:
            title = str(ch_id)
        lines.append(f"{icon} {title} <code>{ch_id}</code>")
        rows.append([B(f"{icon} Toggle {title}", f"fs_toggle_{ch_id}"),
                     B("🗑",                      f"fs_del_{ch_id}")])
    rows.append([B("➕ Add Channel", "fs_add"), B("« Back", "pn_main")])
    body = "\n".join(lines) if lines else "<i>No channels added.</i>"
    return f"📢 <b>Force Subscribe</b>\n\n{body}", InlineKeyboardMarkup(inline_keyboard=rows)


async def batchmsg_panel():
    start = await CosmicBotz.get_batch_start()
    end   = await CosmicBotz.get_batch_end()
    s_st  = f"✅ {start['type']}" if start else "❌ Not set"
    e_st  = f"✅ {end['type']}"   if end   else "❌ Not set"
    return (
        f"📦 <b>Batch Wrapper Messages</b>\n\n"
        f"🟩 Start message: <b>{s_st}</b>\n"
        f"🟥 End message:   <b>{e_st}</b>\n\n"
        f"These send before/after every file delivery.",
        KB(
            [B("✏️ Set Start", "bm_set_start"), B("🗑 Clear Start", "bm_clear_start")],
            [B("✏️ Set End",   "bm_set_end"),   B("🗑 Clear End",   "bm_clear_end")],
            [B("« Back", "pn_main")],
        )
    )


async def admins_panel():
    admins = await CosmicBotz.get_all_admins()
    lines  = [f"• <code>{OWNER_ID}</code> (Owner)"] + [f"• <code>{a}</code>" for a in admins]
    rows   = [[B(f"🗑 Remove {a}", f"adm_del_{a}")] for a in admins]
    rows.append([B("➕ Add Admin", "adm_add"), B("« Back", "pn_main")])
    return (
        f"👮 <b>Admins ({len(admins)+1})</b>\n\n" + "\n".join(lines),
        InlineKeyboardMarkup(inline_keyboard=rows)
    )


async def banned_panel():
    banned = await CosmicBotz.get_ban_users()
    rows   = [[B(f"✅ Unban {u}", f"ubn_{u}")] for u in banned[:15]]
    rows.append([B("« Back", "pn_main")])
    body = "\n".join(f"• <code>{u}</code>" for u in banned) if banned else "<i>None</i>"
    return f"🚫 <b>Banned ({len(banned)})</b>\n\n{body}", InlineKeyboardMarkup(inline_keyboard=rows)


async def log_panel():
    ch = await CosmicBotz.get_log_channel()
    return (
        f"📋 <b>Log Channel</b>\n\nCurrent: {'<code>'+str(ch)+'</code>' if ch else '<i>Not set</i>'}\n\n"
        f"Genlink/batch activity is forwarded here.",
        KB([B("✏️ Set", "log_set"), B("🗑 Clear", "log_clear")], [B("« Back", "pn_main")])
    )


async def stats_panel():
    users = len(await CosmicBotz.full_userbase())
    ban   = len(await CosmicBotz.get_ban_users())
    adm   = len(await CosmicBotz.get_all_admins())
    chs   = len(await CosmicBotz.show_channels())
    tm    = await CosmicBotz.get_del_timer()
    return (
        f"📊 <b>Stats</b>\n\n"
        f"👤 Users: <b>{users}</b>\n🚫 Banned: <b>{ban}</b>\n"
        f"👮 Admins: <b>{adm}</b>\n📢 FSub: <b>{chs}</b>\n"
        f"⏱ Timer: <b>{human_readable_time(tm) if tm else 'Off'}</b>",
        KB([B("« Back", "pn_main")])
    )


async def _edit(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup):
    await callback.message.edit_text(text, reply_markup=markup)


# ── /panel ─────────────────────────────────────────────────────────────────────

@router.message(Command("panel"), is_admin)
async def panel_cmd(message: Message):
    text, markup = await main_panel()
    await message.answer(text, reply_markup=markup)


# ── Navigation ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "pn_main",    is_admin)
async def cb_main(c: CallbackQuery):      t, m = await main_panel();      await _edit(c, t, m)

@router.callback_query(F.data == "pn_close")
async def cb_close(c: CallbackQuery):     await c.message.delete()

@router.callback_query(F.data == "pn_autodel", is_admin)
async def cb_autodel(c: CallbackQuery):   t, m = await autodel_panel();   await _edit(c, t, m)

@router.callback_query(F.data == "pn_caption", is_admin)
async def cb_caption(c: CallbackQuery):   t, m = await caption_panel();   await _edit(c, t, m)

@router.callback_query(F.data == "pn_fsub",    is_admin)
async def cb_fsub(c: CallbackQuery, bot): t, m = await fsub_panel(bot);   await _edit(c, t, m)

@router.callback_query(F.data == "pn_batchmsg",is_admin)
async def cb_batchmsg(c: CallbackQuery):  t, m = await batchmsg_panel();  await _edit(c, t, m)

@router.callback_query(F.data == "pn_admins",  is_admin)
async def cb_admins(c: CallbackQuery):    t, m = await admins_panel();    await _edit(c, t, m)

@router.callback_query(F.data == "pn_banned",  is_admin)
async def cb_banned(c: CallbackQuery):    t, m = await banned_panel();    await _edit(c, t, m)

@router.callback_query(F.data == "pn_log",     is_admin)
async def cb_log(c: CallbackQuery):       t, m = await log_panel();       await _edit(c, t, m)

@router.callback_query(F.data == "pn_stats",   is_admin)
async def cb_stats(c: CallbackQuery):     t, m = await stats_panel();     await _edit(c, t, m)


# ── Auto-delete presets ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("ad_"), is_admin)
async def cb_adset(c: CallbackQuery):
    val = c.data[3:]
    if val == "custom":
        _waiting[c.from_user.id] = "autodel_custom"
        return await c.message.edit_text(
            "⏱ Send auto-delete time in <b>seconds</b>:\n\nExample: <code>3600</code> = 1 hour",
            reply_markup=KB([B("❌ Cancel", "pn_autodel")])
        )
    await CosmicBotz.set_del_timer(int(val))
    label = human_readable_time(int(val)) if int(val) else "Disabled"
    await c.answer(f"✅ Timer set: {label}", show_alert=True)
    t, m = await autodel_panel()
    await _edit(c, t, m)


# ── Caption ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "cap_set", is_admin)
async def cb_cap_set(c: CallbackQuery):
    _waiting[c.from_user.id] = "caption"
    await c.message.edit_text(
        "💬 <b>Send your caption template:</b>\n\n"
        "Variables: <code>{title}</code> <code>{clean_title}</code> <code>{episode}</code> "
        "<code>{season}</code> <code>{quality}</code> <code>{extension}</code>\n\n"
        "Example:\n<code>🎬 {clean_title}\n📺 S{season}E{episode} | {quality}</code>",
        reply_markup=KB([B("❌ Cancel", "pn_caption")])
    )

@router.callback_query(F.data == "cap_clear", is_admin)
async def cb_cap_clear(c: CallbackQuery):
    await CosmicBotz.set_caption("")
    await c.answer("✅ Caption cleared")
    t, m = await caption_panel()
    await _edit(c, t, m)


# ── Force sub ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fs_toggle_"), is_admin)
async def cb_fs_toggle(c: CallbackQuery, bot):
    ch_id   = int(c.data.split("_")[2])
    current = await CosmicBotz.get_channel_mode(ch_id)
    new     = "off" if current == "on" else "on"
    await CosmicBotz.set_channel_mode(ch_id, new)
    await c.answer("🟢 Enabled" if new == "on" else "🔴 Disabled")
    t, m = await fsub_panel(bot)
    await _edit(c, t, m)

@router.callback_query(F.data.startswith("fs_del_"), is_admin)
async def cb_fs_del(c: CallbackQuery, bot):
    ch_id = int(c.data.split("_")[2])
    await CosmicBotz.rem_channel(ch_id)
    await c.answer("🗑 Removed")
    t, m = await fsub_panel(bot)
    await _edit(c, t, m)

@router.callback_query(F.data == "fs_add", is_admin)
async def cb_fs_add(c: CallbackQuery):
    _waiting[c.from_user.id] = "fsub_add"
    await c.message.edit_text(
        "📢 <b>Send the channel ID:</b>\n\nExample: <code>-1002345678901</code>\n<i>Bot must be admin there.</i>",
        reply_markup=KB([B("❌ Cancel", "pn_fsub")])
    )


# ── Batch messages ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "bm_set_start", is_admin)
async def cb_bm_set_start(c: CallbackQuery):
    _waiting[c.from_user.id] = "batch_start"
    await c.message.edit_text(
        "🟩 <b>Send the START message</b> (text, photo or video):",
        reply_markup=KB([B("❌ Cancel", "pn_batchmsg")])
    )

@router.callback_query(F.data == "bm_set_end", is_admin)
async def cb_bm_set_end(c: CallbackQuery):
    _waiting[c.from_user.id] = "batch_end"
    await c.message.edit_text(
        "🟥 <b>Send the END message</b> (text, photo or video):",
        reply_markup=KB([B("❌ Cancel", "pn_batchmsg")])
    )

@router.callback_query(F.data == "bm_clear_start", is_admin)
async def cb_bm_clear_start(c: CallbackQuery):
    await CosmicBotz.del_batch_start()
    await c.answer("✅ Cleared")
    t, m = await batchmsg_panel()
    await _edit(c, t, m)

@router.callback_query(F.data == "bm_clear_end", is_admin)
async def cb_bm_clear_end(c: CallbackQuery):
    await CosmicBotz.del_batch_end()
    await c.answer("✅ Cleared")
    t, m = await batchmsg_panel()
    await _edit(c, t, m)


# ── Admins ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_del_"), is_owner)
async def cb_adm_del(c: CallbackQuery):
    uid = int(c.data.split("_")[2])
    await CosmicBotz.del_admin(uid)
    await c.answer(f"✅ Removed {uid}")
    t, m = await admins_panel()
    await _edit(c, t, m)

@router.callback_query(F.data == "adm_add", is_owner)
async def cb_adm_add(c: CallbackQuery):
    _waiting[c.from_user.id] = "admin_add"
    await c.message.edit_text(
        "👮 <b>Send the user ID to promote:</b>",
        reply_markup=KB([B("❌ Cancel", "pn_admins")])
    )


# ── Banned ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("ubn_"), is_admin)
async def cb_unban(c: CallbackQuery):
    uid = int(c.data.split("_")[1])
    await CosmicBotz.del_ban_user(uid)
    await c.answer(f"✅ Unbanned {uid}")
    t, m = await banned_panel()
    await _edit(c, t, m)


# ── Log channel ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "log_set", is_admin)
async def cb_log_set(c: CallbackQuery):
    _waiting[c.from_user.id] = "log_set"
    await c.message.edit_text(
        "📋 <b>Send the log channel ID:</b>\n\nExample: <code>-1002345678901</code>",
        reply_markup=KB([B("❌ Cancel", "pn_log")])
    )

@router.callback_query(F.data == "log_clear", is_admin)
async def cb_log_clear(c: CallbackQuery):
    await CosmicBotz.set_log_channel(0)
    await c.answer("✅ Cleared")
    t, m = await log_panel()
    await _edit(c, t, m)


# ── Input handler (catches text responses to panel prompts) ────────────────────

@router.message(is_admin, F.chat.type == "private")
async def panel_input(message: Message, bot):
    uid    = message.from_user.id
    action = _waiting.pop(uid, None)
    if not action:
        return

    if action == "autodel_custom":
        try:
            secs = int(message.text.strip())
            await CosmicBotz.set_del_timer(secs)
            label = human_readable_time(secs) if secs else "Disabled"
            await message.answer(f"✅ Timer set to <b>{label}</b>.\n\nSend /panel to return.")
        except ValueError:
            await message.answer("❌ Send a number in seconds.")

    elif action == "caption":
        tpl = message.text or message.caption or ""
        if not tpl:
            return await message.answer("❌ Send a text caption template.")
        await CosmicBotz.set_caption(tpl)
        from helper.caption_parser import render_caption
        preview = render_caption(tpl, "Attack.on.Titan.S04E28.1080p.mkv")
        await message.answer(
            f"✅ <b>Caption saved!</b>\n\n<b>Preview:</b>\n<blockquote>{preview}</blockquote>\n\nSend /panel to return."
        )

    elif action == "fsub_add":
        try:
            ch_id = int(message.text.strip())
            chat  = await bot.get_chat(ch_id)
            me    = await bot.get_me()
            mbr   = await bot.get_chat_member(ch_id, me.id)
            if mbr.status not in ("administrator", "creator"):
                return await message.answer("❌ Bot must be admin in that channel.")
            await CosmicBotz.add_channel(ch_id)
            await message.answer(f"✅ Added <b>{chat.title}</b> <code>{ch_id}</code>\n\nSend /panel to return.")
        except Exception as e:
            await message.answer(f"❌ {e}")

    elif action in ("batch_start", "batch_end"):
        data = None
        if message.photo:
            data = {"type": "photo", "file_id": message.photo[-1].file_id, "caption": message.caption or ""}
        elif message.video:
            data = {"type": "video", "file_id": message.video.file_id, "caption": message.caption or ""}
        elif message.text:
            data = {"type": "text", "content": message.text}
        if not data:
            return await message.answer("❌ Send text, photo, or video.")
        if action == "batch_start":
            await CosmicBotz.set_batch_start(data)
            await message.answer("✅ <b>Start message saved.</b>\n\nSend /panel to return.")
        else:
            await CosmicBotz.set_batch_end(data)
            await message.answer("✅ <b>End message saved.</b>\n\nSend /panel to return.")

    elif action == "admin_add":
        try:
            target = int(message.text.strip())
            await CosmicBotz.add_admin(target)
            await message.answer(f"✅ <code>{target}</code> is now admin.\n\nSend /panel to return.")
        except ValueError:
            await message.answer("❌ Invalid user ID.")

    elif action == "log_set":
        try:
            ch_id = int(message.text.strip())
            await bot.get_chat(ch_id)
            await CosmicBotz.set_log_channel(ch_id)
            await message.answer(f"✅ Log channel set to <code>{ch_id}</code>\n\nSend /panel to return.")
        except Exception as e:
            await message.answer(f"❌ {e}")
