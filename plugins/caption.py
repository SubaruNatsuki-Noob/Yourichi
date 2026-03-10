"""
Caption template management.
Variables: {title} {clean_title} {episode} {season} {quality} {extension}
"""
import functools

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import CUSTOM_CAPTION
from database.database import CosmicBotz
from helper import is_admin, render_caption

router = Router()

VARIABLE_HELP = (
    "\n\n<b>📝 Available Variables:</b>\n"
    "<code>{title}</code>       — full file title\n"
    "<code>{clean_title}</code> — anime/show name only\n"
    "<code>{episode}</code>     — episode number (01, 02…)\n"
    "<code>{season}</code>      — season number  (01, 02…)\n"
    "<code>{quality}</code>     — 1080p / 720p / 4K…\n"
    "<code>{extension}</code>   — mkv / mp4…\n\n"
    "<b>Example template:</b>\n"
    "<code>🎬 {clean_title}\n"
    "📺 Season {season} | Episode {episode}\n"
    "🎞 {quality} | {extension}\n\n"
    "• @YourChannel</code>"
)


@router.message(Command("setcaption"), is_admin)
@functools.wraps(lambda m, **kw: None)
async def setcaption_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer(
            "❌ Usage: <code>/setcaption &lt;template&gt;</code>" + VARIABLE_HELP
        )
    template = args[1].strip()
    await CosmicBotz.set_caption(template)
    preview = render_caption(template, "Attack.on.Titan.S04E28.1080p.mkv")
    await message.answer(
        f"✅ <b>Caption template saved!</b>\n\n"
        f"<b>Preview with test filename:</b>\n"
        f"<blockquote>{preview}</blockquote>"
    )


@router.message(Command("getcaption"), is_admin)
@functools.wraps(lambda m, **kw: None)
async def getcaption_cmd(message: Message):
    template = await CosmicBotz.get_caption() or CUSTOM_CAPTION
    await message.answer(
        f"<b>📋 Current Caption Template:</b>\n\n<code>{template}</code>" + VARIABLE_HELP
    )


@router.message(Command("delcaption"), is_admin)
@functools.wraps(lambda m, **kw: None)
async def delcaption_cmd(message: Message):
    await CosmicBotz.set_caption("")
    await message.answer("✅ Caption template cleared. Files will use their original captions.")
