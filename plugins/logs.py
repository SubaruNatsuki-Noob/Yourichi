"""
/logs — view recent log, edit log text inline, or send as .txt file.
"""
import io
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from config import LOG_FILE_NAME
from helper import is_admin

router = Router()
logger = logging.getLogger(__name__)

_editing = {}  # uid -> True


def _log_markup():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Send as .txt", callback_data="log_send_txt")],
        [InlineKeyboardButton(text="✏️ Edit log text", callback_data="log_edit")],
        [InlineKeyboardButton(text="🗑 Clear log file", callback_data="log_clear_file")],
        [InlineKeyboardButton(text="❌ Close",          callback_data="log_close")],
    ])


@router.message(Command("logs"), is_admin)
async def logs_cmd(message: Message):
    try:
        with open(LOG_FILE_NAME, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # Show last 3000 chars in message
        preview = content[-3000:] if len(content) > 3000 else content
        if not preview.strip():
            preview = "<i>Log file is empty.</i>"
        else:
            preview = f"<pre>{preview}</pre>"
    except FileNotFoundError:
        preview = "<i>Log file not found.</i>"

    await message.answer(
        f"📋 <b>Bot Logs</b>\n\n{preview}",
        reply_markup=_log_markup(),
    )


@router.callback_query(F.data == "log_send_txt", is_admin)
async def log_send_txt(callback: CallbackQuery):
    try:
        with open(LOG_FILE_NAME, "rb") as f:
            data = f.read()
        await callback.message.answer_document(
            BufferedInputFile(data, filename="bot_logs.txt"),
            caption="📄 Full log file"
        )
        await callback.answer("✅ Sent as file")
    except FileNotFoundError:
        await callback.answer("❌ Log file not found", show_alert=True)


@router.callback_query(F.data == "log_edit", is_admin)
async def log_edit_start(callback: CallbackQuery):
    _editing[callback.from_user.id] = True
    await callback.message.edit_text(
        "✏️ <b>Send the new log content</b> to replace the current log file:\n\n"
        "<i>(Send any text to overwrite the log)</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="log_edit_cancel")]
        ])
    )


@router.callback_query(F.data == "log_edit_cancel", is_admin)
async def log_edit_cancel(callback: CallbackQuery):
    _editing.pop(callback.from_user.id, None)
    await logs_cmd.__wrapped__(callback.message) if hasattr(logs_cmd, "__wrapped__") else None
    await callback.answer("Cancelled")
    await callback.message.delete()


@router.callback_query(F.data == "log_clear_file", is_admin)
async def log_clear_file(callback: CallbackQuery):
    try:
        open(LOG_FILE_NAME, "w").close()
        await callback.answer("✅ Log file cleared", show_alert=True)
        await callback.message.edit_text("📋 <b>Log file cleared.</b>", reply_markup=_log_markup())
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)


@router.callback_query(F.data == "log_close")
async def log_close(callback: CallbackQuery):
    await callback.message.delete()


@router.message(is_admin, F.chat.type == "private", F.text)
async def log_edit_input(message: Message):
    uid = message.from_user.id
    if not _editing.pop(uid, None):
        return
    try:
        with open(LOG_FILE_NAME, "w", encoding="utf-8") as f:
            f.write(message.text)
        await message.answer("✅ <b>Log file updated.</b>", reply_markup=_log_markup())
    except Exception as e:
        await message.answer(f"❌ {e}")
