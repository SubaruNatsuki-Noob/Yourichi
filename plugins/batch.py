"""
/batch        — First & last msg ID from DB channel → instant link
/custom_batch — Send files here → /done → link (stored in DB channel with caption)
/done         — Finish session
/cancel       — Cancel any session
/pro_batch    — Wizard: first post → last post → scan range → sort by ep+quality
"""
import re
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ContentType

from config import CHANNEL_ID
from database.database import CosmicBotz
from helper import is_admin, encode_file_id
from helper.utils import parse_tg_url
from helper.caption_parser import parse_filename
from helper.delivery import store_file_with_caption

router = Router()
logger = logging.getLogger(__name__)

MEDIA_TYPES = {
    ContentType.DOCUMENT, ContentType.VIDEO, ContentType.AUDIO,
    ContentType.PHOTO, ContentType.ANIMATION, ContentType.VOICE, ContentType.VIDEO_NOTE,
}

_sessions:     dict = {}  # uid -> {"mode": "custom", "msg_ids": []}
_batch_wizard: dict = {}  # uid -> {"step": "first"|"last", "first_id": int}
_pro_wizard:   dict = {}  # uid -> {"step": "first"|"last", "chat_ref": str, "first_msg": int}


async def _try_log(bot, text: str, link: str):
    log_ch = await CosmicBotz.get_log_channel()
    if not log_ch:
        return
    try:
        await bot.send_message(
            log_ch, f"{text}\n{link}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Open", url=link)]
            ]),
            disable_web_page_preview=True,
        )
    except Exception:
        pass


# ── /batch ─────────────────────────────────────────────────────────────────────

@router.message(Command("batch"), is_admin)
async def batch_cmd(message: Message):
    _batch_wizard[message.from_user.id] = {"step": "first"}
    await message.answer(
        "📦 <b>Batch Link Generator</b>\n\n"
        "Step 1/2 — Send the <b>first message ID</b> from your DB channel:"
    )


@router.message(is_admin, F.chat.type == "private", F.text.regexp(r"^\d+$"))
async def batch_wizard_input(message: Message, bot):
    uid   = message.from_user.id
    state = _batch_wizard.get(uid)
    if not state:
        return

    msg_id = int(message.text.strip())

    if state["step"] == "first":
        _batch_wizard[uid] = {"step": "last", "first_id": msg_id}
        return await message.answer(
            f"✅ First ID: <code>{msg_id}</code>\n\n"
            f"Step 2/2 — Now send the <b>last message ID</b>:"
        )

    first_id = state["first_id"]
    last_id  = msg_id
    del _batch_wizard[uid]
    if last_id < first_id:
        first_id, last_id = last_id, first_id

    param = f"batch_{first_id}_{last_id}"
    me    = await bot.get_me()
    link  = f"https://t.me/{me.username}?start={param}"
    count = last_id - first_id + 1

    await message.answer(
        f"✅ <b>Batch link created!</b>\n\n📦 Files: <b>{count}</b>  (IDs {first_id}–{last_id})\n🔗 {link}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Share Link", url=link)]
        ]),
        disable_web_page_preview=True,
    )
    await _try_log(bot, f"📦 Batch | {count} files | IDs {first_id}–{last_id}", link)


# ── /custom_batch ──────────────────────────────────────────────────────────────

@router.message(Command("custom_batch"), is_admin)
async def custom_batch_cmd(message: Message):
    _sessions[message.from_user.id] = {"mode": "custom", "msg_ids": []}
    await message.answer(
        "📁 <b>Custom Batch mode!</b>\n\n"
        "Send or forward files — each one is stored in the DB channel with caption applied.\n\n"
        "/done → get link\n/cancel → abort"
    )


# ── /done ──────────────────────────────────────────────────────────────────────

@router.message(Command("done"), is_admin)
async def done_cmd(message: Message, bot):
    uid     = message.from_user.id
    session = _sessions.pop(uid, None)
    if not session:
        return await message.answer("❌ No active session.")

    msg_ids = session.get("msg_ids", [])
    if not msg_ids:
        return await message.answer("❌ No files collected yet.")

    me            = await bot.get_me()
    encoded_parts = [encode_file_id(CHANNEL_ID, mid) for mid in msg_ids]
    param         = "cb_" + "_".join(encoded_parts)
    link          = f"https://t.me/{me.username}?start={param}"

    await message.answer(
        f"✅ <b>Custom batch link!</b>\n\n📦 Files: <b>{len(msg_ids)}</b>\n🔗 {link}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Share Link", url=link)]
        ]),
        disable_web_page_preview=True,
    )
    await _try_log(bot, f"📁 Custom batch | {len(msg_ids)} files", link)


# ── /cancel ────────────────────────────────────────────────────────────────────

@router.message(Command("cancel"), is_admin)
async def cancel_cmd(message: Message):
    uid = message.from_user.id
    if _sessions.pop(uid, None) or _batch_wizard.pop(uid, None) or _pro_wizard.pop(uid, None):
        await message.answer("❌ Session cancelled.")
    else:
        await message.answer("No active session.")


# ── Media collector — custom_batch only ────────────────────────────────────────

@router.message(is_admin, F.chat.type == "private", F.content_type.in_(MEDIA_TYPES),
    F.func(lambda m: _sessions.get(m.from_user.id, {}).get("mode") == "custom"))
async def collect_media(message: Message, bot):
    uid     = message.from_user.id
    session = _sessions.get(uid)

    # Store in DB channel AND apply caption at store time
    msg_id = await store_file_with_caption(bot, message)
    if not msg_id:
        return await message.answer("❌ Failed to store file.")

    session["msg_ids"].append(msg_id)
    n = len(session["msg_ids"])
    await message.answer(f"✅ File <b>{n}</b> stored with caption. Send more or /done.")


# ── /pro_batch — wizard: forward/URL first → last ─────────────────────────────

@router.message(Command("pro_batch"), is_admin)
async def pro_batch_cmd(message: Message):
    _pro_wizard[message.from_user.id] = {"step": "first"}
    await message.answer(
        "🚀 <b>Pro Batch</b>\n\n"
        "Step 1/2 — Forward or paste the <b>first post</b> from your channel.\n\n"
        "Accepted:\n"
        "• Forward the message here\n"
        "• Paste URL: <code>https://t.me/c/1234567890/100</code>\n\n"
        "/cancel to abort."
    )


@router.message(is_admin, F.chat.type == "private", F.func(lambda m: m.from_user.id in _pro_wizard))
async def pro_wizard_input(message: Message, bot):
    uid   = message.from_user.id
    state = _pro_wizard.get(uid)
    if not state:
        return

    chat_ref, msg_id = _extract_ref(message)
    if not chat_ref or not msg_id:
        return await message.answer(
            "❌ Couldn't parse. Forward a channel post or paste a <code>t.me</code> link."
        )

    if state["step"] == "first":
        _pro_wizard[uid] = {"step": "last", "chat_ref": chat_ref, "first_msg": msg_id}
        return await message.answer(
            f"✅ First post: ID <code>{msg_id}</code>\n\n"
            f"Step 2/2 — Now forward or paste the <b>last post</b> from the same channel:"
        )

    # step == last
    first_msg = state["first_msg"]
    chat_ref  = state["chat_ref"]
    last_msg  = msg_id
    del _pro_wizard[uid]

    if last_msg < first_msg:
        first_msg, last_msg = last_msg, first_msg

    total = last_msg - first_msg + 1
    wait  = await message.answer(
        f"🔍 Scanning <b>{total}</b> posts...\n<i>Please wait.</i>"
    )
    await _process_pro_batch(message, bot, chat_ref, first_msg, last_msg, wait)


def _extract_ref(message: Message) -> tuple:
    """Get (chat_ref, msg_id) from a forwarded post or URL in text."""
    if message.forward_from_chat and message.forward_from_message_id:
        return str(message.forward_from_chat.id), message.forward_from_message_id
    if message.text:
        urls = re.findall(r"https?://t\.me/\S+", message.text)
        if urls:
            return parse_tg_url(urls[0])
    return None, None


# ── Pro batch processor ────────────────────────────────────────────────────────

def _norm_q(q: str) -> str:
    q = q.lower()
    if q in ("4k", "2160p"):  return "2160p"
    if q in ("fhd", "1080p"): return "1080p"
    if q in ("hd", "720p"):   return "720p"
    return q

def _q_rank(q: str) -> int:
    order = ["144p","240p","360p","480p","540p","720p","1080p","1440p","2160p"]
    try:    return order.index(_norm_q(q))
    except: return 99


async def _process_pro_batch(
    message: Message, bot, chat_ref: str, first_msg: int, last_msg: int, wait_msg
):
    files  = []
    failed = 0

    for mid in range(first_msg, last_msg + 1):
        try:
            # Forward to bot's DM to read metadata
            fwd = await bot.forward_message(
                chat_id=message.chat.id,
                from_chat_id=chat_ref,
                message_id=mid,
            )
            fname = (
                (fwd.document  and fwd.document.file_name)
                or (fwd.video  and (fwd.video.file_name or "video.mp4"))
                or (fwd.audio  and (fwd.audio.file_name or "audio.mp3"))
                or "file"
            )
            meta    = parse_filename(fname)
            quality = _norm_q(meta.get("quality") or "unknown")
            ep_raw  = meta.get("episode") or "0"
            episode = int(ep_raw) if str(ep_raw).isdigit() else 0

            # Store in DB channel with caption applied at store time
            stored_id = await store_file_with_caption(bot, fwd)
            try:
                await bot.delete_message(message.chat.id, fwd.message_id)
            except Exception:
                pass

            if stored_id:
                files.append({
                    "fname":   fname,
                    "episode": episode,
                    "quality": quality,
                    "msg_id":  stored_id,
                })
        except Exception as e:
            logger.warning(f"pro_batch mid={mid}: {e}")
            failed += 1

    if not files:
        return await wait_msg.edit_text(
            f"❌ No valid files found in posts {first_msg}–{last_msg}."
        )

    files.sort(key=lambda f: (f["episode"], _q_rank(f["quality"])))

    me      = await bot.get_me()
    lines   = [f"<b>🎬 Pro Batch</b> ({len(files)} files)\n"]
    buttons = []

    by_q: dict = {}
    for f in files:
        by_q.setdefault(f["quality"], []).append(f)

    for q in sorted(by_q.keys(), key=_q_rank):
        group = by_q[q]
        enc   = [encode_file_id(CHANNEL_ID, f["msg_id"]) for f in group]
        param = "cb_" + "_".join(enc)
        link  = f"https://t.me/{me.username}?start={param}"
        lines.append(f"\n<b>📺 {q.upper()}</b>")
        for f in group:
            ep = f"Ep {f['episode']:02d}" if f["episode"] else "–"
            lines.append(f"  • {ep} — {f['fname'][:45]}")
        buttons.append([InlineKeyboardButton(text=f"📥 {q.upper()} ({len(group)})", url=link)])

    all_enc   = [encode_file_id(CHANNEL_ID, f["msg_id"]) for f in files]
    all_param = "cb_" + "_".join(all_enc)
    all_link  = f"https://t.me/{me.username}?start={all_param}"
    buttons.insert(0, [InlineKeyboardButton(text=f"📦 All ({len(files)} files)", url=all_link)])

    if failed:
        lines.append(f"\n<i>⚠️ {failed} post(s) skipped</i>")

    await wait_msg.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        disable_web_page_preview=True,
    )
    await _try_log(bot, f"🚀 Pro Batch | {len(files)} files", all_link)
