"""
Batch commands:
/batch        — Ask first & last msg ID from DB channel → instant link
/custom_batch — Send files here → /done → link (files auto-stored in DB channel)
/done         — Finish custom_batch session
/cancel       — Cancel any active session
/pro_batch    — Paste post URLs → scan, sort by episode+quality → structured links
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

router = Router()
logger = logging.getLogger(__name__)

MEDIA_TYPES = {
    ContentType.DOCUMENT, ContentType.VIDEO, ContentType.AUDIO,
    ContentType.PHOTO, ContentType.ANIMATION, ContentType.VOICE, ContentType.VIDEO_NOTE,
}

_sessions: dict = {}      # uid -> {"mode": "custom"|"pro", "msg_ids": [], "urls": []}
_batch_wizard: dict = {}  # uid -> {"step": "first"|"last", "first_id": int}


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

    # step == "last"
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
        f"✅ <b>Batch link created!</b>\n\n"
        f"📦 Files: <b>{count}</b>  (IDs {first_id}–{last_id})\n"
        f"🔗 {link}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Share Link", url=link)]
        ]),
        disable_web_page_preview=True,
    )
    log_ch = await CosmicBotz.get_log_channel()
    if log_ch:
        try:
            await bot.send_message(
                log_ch,
                f"📦 <b>Batch link</b>\nFiles: {count} | IDs: {first_id}–{last_id}\n{link}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔗 Share", url=link)]
                ]),
                disable_web_page_preview=True,
            )
        except Exception:
            pass


# ── /custom_batch ──────────────────────────────────────────────────────────────

@router.message(Command("custom_batch"), is_admin)
async def custom_batch_cmd(message: Message):
    _sessions[message.from_user.id] = {"mode": "custom", "msg_ids": []}
    await message.answer(
        "📁 <b>Custom Batch mode!</b>\n\n"
        "Send or forward files here — each one is stored automatically.\n\n"
        "/done → generate link\n"
        "/cancel → abort"
    )


# ── /done ──────────────────────────────────────────────────────────────────────

@router.message(Command("done"), is_admin)
async def done_cmd(message: Message, bot):
    uid     = message.from_user.id
    session = _sessions.pop(uid, None)

    if not session:
        return await message.answer("❌ No active session. Start one with /custom_batch or /pro_batch.")

    msg_ids = session.get("msg_ids", [])

    # pro_batch mode — URLs collected, now process them
    if session.get("mode") == "pro" and session.get("urls"):
        return await _process_pro_batch(message, bot, session["urls"])

    if not msg_ids:
        return await message.answer("❌ No files collected yet.")

    me    = await bot.get_me()
    param = "cb_" + "_".join(str(i) for i in msg_ids)
    link  = f"https://t.me/{me.username}?start={param}"

    await message.answer(
        f"✅ <b>Custom batch link!</b>\n\n"
        f"📦 Files: <b>{len(msg_ids)}</b>\n"
        f"🔗 {link}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Share Link", url=link)]
        ]),
        disable_web_page_preview=True,
    )
    log_ch = await CosmicBotz.get_log_channel()
    if log_ch:
        try:
            await bot.send_message(
                log_ch,
                f"📁 <b>Custom batch</b>\nFiles: {len(msg_ids)}\n{link}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔗 Share", url=link)]
                ]),
                disable_web_page_preview=True,
            )
        except Exception:
            pass


# ── /cancel ────────────────────────────────────────────────────────────────────

@router.message(Command("cancel"), is_admin)
async def cancel_cmd(message: Message):
    uid = message.from_user.id
    if _sessions.pop(uid, None) or _batch_wizard.pop(uid, None):
        await message.answer("❌ Session cancelled.")
    else:
        await message.answer("No active session.")


# ── Media collector — only during custom_batch session ─────────────────────────

@router.message(is_admin, F.chat.type == "private", F.content_type.in_(MEDIA_TYPES))
async def collect_media(message: Message):
    uid     = message.from_user.id
    session = _sessions.get(uid)
    if not session or session["mode"] != "custom":
        return  # pass to auto_genlink in links.py

    try:
        stored = await message.copy_to(CHANNEL_ID)
        session["msg_ids"].append(stored.message_id)
        n = len(session["msg_ids"])
        await message.answer(f"✅ File <b>{n}</b> stored. Send more or /done.")
    except Exception as e:
        logger.error(f"collect_media: {e}")
        await message.answer(f"❌ Failed to store:\n<code>{e}</code>")


# ── /pro_batch ─────────────────────────────────────────────────────────────────

QUALITY_RE = re.compile(
    r"(2160[Pp]|1440[Pp]|1080[Pp]|720[Pp]|540[Pp]|480[Pp]|360[Pp]|240[Pp]|144[Pp]|4[Kk]|FHD|fhd|HD|hd)",
    re.IGNORECASE,
)


def _norm_quality(q: str) -> str:
    q = q.lower()
    if q in ("4k", "2160p"):    return "2160p"
    if q in ("fhd", "1080p"):   return "1080p"
    if q in ("hd", "720p"):     return "720p"
    return q


def _quality_rank(q: str) -> int:
    order = ["144p","240p","360p","480p","540p","720p","1080p","1440p","2160p"]
    try:
        return order.index(_norm_quality(q))
    except ValueError:
        return 99


@router.message(Command("pro_batch"), is_admin)
async def pro_batch_cmd(message: Message, bot):
    text = message.text or ""
    urls = re.findall(r"https?://t\.me/\S+", text)

    if urls:
        return await _process_pro_batch(message, bot, urls)

    # No URLs inline — start collection session
    _sessions[message.from_user.id] = {"mode": "pro", "msg_ids": [], "urls": []}
    await message.answer(
        "🚀 <b>Pro Batch mode!</b>\n\n"
        "Paste your channel post URLs (one per line or space-separated).\n\n"
        "<b>Supported formats:</b>\n"
        "• <code>https://t.me/channelname/123</code>\n"
        "• <code>https://t.me/c/1234567890/123</code>\n\n"
        "Send /done when finished."
    )


@router.message(is_admin, F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def pro_batch_url_input(message: Message, bot):
    uid     = message.from_user.id
    session = _sessions.get(uid)
    if not session or session.get("mode") != "pro":
        return

    urls = re.findall(r"https?://t\.me/\S+", message.text or "")
    if not urls:
        return

    session.setdefault("urls", []).extend(urls)
    await message.answer(
        f"✅ <b>{len(urls)}</b> URL(s) added. Total: <b>{len(session['urls'])}</b>\n\n"
        "Send more or /done."
    )


async def _process_pro_batch(message: Message, bot, urls: list):
    wait  = await message.answer(f"🔍 Scanning <b>{len(urls)}</b> URLs...")
    files = []

    for url in urls:
        chat_ref, msg_id = parse_tg_url(url)
        if not chat_ref or not msg_id:
            continue
        try:
            msg = await bot.forward_message(
                chat_id=message.chat.id,
                from_chat_id=chat_ref,
                message_id=msg_id,
            )
            fname = (
                (msg.document  and msg.document.file_name)
                or (msg.video  and (msg.video.file_name or "video.mp4"))
                or (msg.audio  and (msg.audio.file_name or "audio.mp3"))
                or "file"
            )
            meta    = parse_filename(fname)
            quality = _norm_quality(meta.get("quality") or "unknown")
            ep_raw  = meta.get("episode") or "0"
            episode = int(ep_raw) if str(ep_raw).isdigit() else 0

            stored = await msg.copy_to(CHANNEL_ID)
            try:
                await bot.delete_message(message.chat.id, msg.message_id)
            except Exception:
                pass

            files.append({
                "fname":   fname,
                "episode": episode,
                "quality": quality,
                "msg_id":  stored.message_id,
            })
        except Exception as e:
            logger.warning(f"pro_batch {url}: {e}")

    if not files:
        return await wait.edit_text("❌ No valid files found from the provided URLs.")

    files.sort(key=lambda f: (f["episode"], _quality_rank(f["quality"])))

    me      = await bot.get_me()
    lines   = ["<b>🎬 Pro Batch Results</b>\n"]
    buttons = []

    # Group by quality
    by_quality: dict = {}
    for f in files:
        by_quality.setdefault(f["quality"], []).append(f)

    for quality in sorted(by_quality.keys(), key=_quality_rank):
        group   = by_quality[quality]
        ids     = [f["msg_id"] for f in group]
        param   = "cb_" + "_".join(str(i) for i in ids)
        link    = f"https://t.me/{me.username}?start={param}"
        lines.append(f"\n<b>📺 {quality.upper()}</b>")
        for f in group:
            ep = f"Ep {f['episode']:02d}" if f["episode"] else "–"
            lines.append(f"  • {ep} — {f['fname'][:45]}")
        lines.append(f"  🔗 <a href='{link}'>Get {quality.upper()} ({len(group)} files)</a>")
        buttons.append([InlineKeyboardButton(text=f"📥 {quality.upper()} ({len(group)})", url=link)])

    # Master link — all files
    all_ids   = [f["msg_id"] for f in files]
    all_param = "cb_" + "_".join(str(i) for i in all_ids)
    all_link  = f"https://t.me/{me.username}?start={all_param}"
    buttons.insert(0, [InlineKeyboardButton(text=f"📦 All Qualities ({len(files)} files)", url=all_link)])

    await wait.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        disable_web_page_preview=True,
    )

    log_ch = await CosmicBotz.get_log_channel()
    if log_ch:
        try:
            await bot.send_message(
                log_ch,
                f"🚀 <b>Pro Batch</b>\n{len(files)} files scanned\n{all_link}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📦 All Files", url=all_link)]
                ]),
                disable_web_page_preview=True,
            )
        except Exception:
            pass

    _sessions.pop(message.from_user.id, None)
