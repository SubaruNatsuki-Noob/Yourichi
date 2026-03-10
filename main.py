"""
YourichiFile Store Bot — Aiogram 3
================================
Supports both Webhook (recommended for Render) and Polling mode.
Toggle via WEBHOOK=True/False in your environment variables.
"""
import asyncio
import logging
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import (
    TG_BOT_TOKEN, CHANNEL_ID, OWNER_ID,
    PORT, WEBHOOK, WEBHOOK_URL, WEBHOOK_PATH,
    LOGGER,
)
from database.database import CosmicBotz

from plugins.start   import router as start_router
from plugins.links   import router as links_router
from plugins.batch   import router as batch_router
from plugins.admin   import router as admin_router
from plugins.fsub    import router as fsub_router
from plugins.caption import router as caption_router
from plugins.misc    import router as misc_router

logger = LOGGER(__name__)


# ── Bot commands menu ──────────────────────────────────────────────────────────

async def set_commands(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start",          description="Start the bot"),
        BotCommand(command="help",           description="Help menu"),
        BotCommand(command="about",          description="About this bot"),
        BotCommand(command="stats",          description="[Admin] Bot statistics"),
        BotCommand(command="uptime",         description="Bot uptime"),
        BotCommand(command="genlink",        description="[Admin] Generate shareable link"),
        BotCommand(command="batch",          description="[Admin] Start batch upload session"),
        BotCommand(command="custom_batch",   description="[Admin] Link by specific msg IDs"),
        BotCommand(command="done",           description="[Admin] Finish batch session"),
        BotCommand(command="cancel",         description="[Admin] Cancel batch session"),
        BotCommand(command="setcaption",     description="[Admin] Set caption template"),
        BotCommand(command="getcaption",     description="[Admin] View caption template"),
        BotCommand(command="delcaption",     description="[Admin] Reset caption"),
        BotCommand(command="addchnl",        description="[Admin] Add force-sub channel"),
        BotCommand(command="delchnl",        description="[Admin] Remove force-sub channel"),
        BotCommand(command="listchnl",       description="[Admin] List force-sub channels"),
        BotCommand(command="fsub_mode",      description="[Admin] Toggle force-sub on/off"),
        BotCommand(command="dlt_time",       description="[Admin] Set auto-delete timer"),
        BotCommand(command="check_dlt_time", description="[Admin] View auto-delete timer"),
        BotCommand(command="ban",            description="[Admin] Ban a user"),
        BotCommand(command="unban",          description="[Admin] Unban a user"),
        BotCommand(command="banlist",        description="[Admin] List banned users"),
        BotCommand(command="add_admin",      description="[Owner] Add an admin"),
        BotCommand(command="deladmin",       description="[Owner] Remove an admin"),
        BotCommand(command="admins",         description="[Admin] List all admins"),
        BotCommand(command="dbroadcast",     description="[Admin] Broadcast document/video"),
        BotCommand(command="pbroadcast",     description="[Admin] Broadcast photo"),
        BotCommand(command="delreq",         description="[Admin] Clean leftover req users"),
        BotCommand(command="cmds",           description="[Admin] All admin commands"),
    ])


# ── Startup checks ─────────────────────────────────────────────────────────────

async def on_startup(bot: Bot, **kwargs):
    # Verify DB storage channel
    try:
        await bot.get_chat(CHANNEL_ID)
        test = await bot.send_message(CHANNEL_ID, "✅ Bot startup test — ignore")
        await bot.delete_message(CHANNEL_ID, test.message_id)
    except Exception as e:
        logger.critical(f"DB channel error: {e}")
        logger.critical(
            f"Make sure bot is admin in CHANNEL_ID={CHANNEL_ID} and the value is correct."
        )
        sys.exit(1)

    await set_commands(bot)
    me = await bot.get_me()
    mode = "Webhook" if WEBHOOK else "Polling"
    logger.info(f"Bot started: @{me.username} | Mode: {mode}")

    try:
        await bot.send_message(
            OWNER_ID,
            f"<b>✅ Bot started!</b>\n\n"
            f"🤖 @{me.username}\n"
            f"⚙️ Mode: <b>{mode}</b>"
        )
    except Exception:
        pass


async def on_shutdown(bot: Bot, **kwargs):
    logger.info("Shutting down — removing webhook...")
    await bot.delete_webhook(drop_pending_updates=True)


# ── Dispatcher builder ─────────────────────────────────────────────────────────

def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(start_router)    # /start, file delivery, force-sub gate
    dp.include_router(links_router)    # /genlink
    dp.include_router(batch_router)    # /batch /custom_batch /done /cancel
    dp.include_router(admin_router)    # ban/unban/timer/broadcast/admins
    dp.include_router(fsub_router)     # force-sub channel management + events
    dp.include_router(caption_router)  # /setcaption /getcaption /delcaption
    dp.include_router(misc_router)     # /help /about /stats /uptime + reply guard
    return dp


# ── Webhook mode ───────────────────────────────────────────────────────────────

async def run_webhook(bot: Bot, dp: Dispatcher):
    if not WEBHOOK_URL:
        logger.critical(
            "WEBHOOK=True but WEBHOOK_URL is not set!\n"
            "Set WEBHOOK_URL=https://your-app-name.onrender.com in your env vars."
        )
        sys.exit(1)

    full_webhook_url = f"{WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}"
    logger.info(f"Setting webhook: {full_webhook_url}")

    await bot.set_webhook(
        url=full_webhook_url,
        drop_pending_updates=True,
        allowed_updates=dp.resolve_used_update_types(),
    )

    app = web.Application()

    # Health check endpoint
    async def health(_):
        return web.Response(text="AlisaFile Store Bot is running ✅")
    app.router.add_get("/", health)

    # Register webhook handler
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()

    logger.info(f"Webhook server listening on port {PORT}")
    logger.info(f"Webhook path: {WEBHOOK_PATH}")

    # Keep alive forever
    await asyncio.Event().wait()


# ── Polling mode ───────────────────────────────────────────────────────────────

async def run_polling(bot: Bot, dp: Dispatcher):
    # Remove any leftover webhook
    await bot.delete_webhook(drop_pending_updates=True)

    # Minimal web server (health check for Render even in polling mode)
    async def health(_):
        return web.Response(text="AlisaFile Store Bot is running ✅ (polling mode)")

    app    = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info(f"Health server running on port {PORT} (polling mode)")

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


# ── Entry point ────────────────────────────────────────────────────────────────

async def main():
    # Init database (classmethod singleton — no instance needed)
    CosmicBotz.init()

    bot = Bot(
        token=TG_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher()

    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    if WEBHOOK:
        dp.shutdown.register(on_shutdown)

    if WEBHOOK:
        logger.info("Starting in WEBHOOK mode...")
        await run_webhook(bot, dp)
    else:
        logger.info("Starting in POLLING mode...")
        await run_polling(bot, dp)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
