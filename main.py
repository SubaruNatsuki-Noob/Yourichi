"""
YourichiFile Store Bot — Aiogram 3
Webhook (recommended on Render) or Polling mode via WEBHOOK env var.
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

from config import TG_BOT_TOKEN, CHANNEL_ID, OWNER_ID, PORT, WEBHOOK, WEBHOOK_URL, WEBHOOK_PATH, LOGGER
from database.database import CosmicBotz

from plugins.start   import router as start_router
from plugins.links   import router as links_router
from plugins.batch   import router as batch_router
from plugins.panel   import router as panel_router
from plugins.admin   import router as admin_router
from plugins.fsub    import router as fsub_router
from plugins.caption import router as caption_router
from plugins.logs    import router as logs_router
from plugins.misc    import router as misc_router

logger = LOGGER(__name__)


async def set_commands(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start",        description="Start the bot"),
        BotCommand(command="panel",        description="[Admin] Admin control panel"),
        BotCommand(command="genlink",      description="[Admin] Generate link for a file"),
        BotCommand(command="batch",        description="[Admin] Batch link by first/last ID"),
        BotCommand(command="custom_batch", description="[Admin] Batch by sending files here"),
        BotCommand(command="pro_batch",    description="[Admin] Scan URLs & sort by quality"),
        BotCommand(command="done",         description="[Admin] Finish batch session"),
        BotCommand(command="cancel",       description="[Admin] Cancel session"),
        BotCommand(command="logs",         description="[Admin] View/export bot logs"),
        BotCommand(command="stats",        description="[Admin] Bot statistics"),
        BotCommand(command="uptime",       description="Bot uptime"),
        BotCommand(command="ban",          description="[Admin] Ban a user"),
        BotCommand(command="unban",        description="[Admin] Unban a user"),
        BotCommand(command="banlist",      description="[Admin] List banned users"),
        BotCommand(command="add_admin",    description="[Owner] Add admin"),
        BotCommand(command="deladmin",     description="[Owner] Remove admin"),
        BotCommand(command="admins",       description="[Admin] List admins"),
        BotCommand(command="addchnl",      description="[Admin] Add force-sub channel"),
        BotCommand(command="delchnl",      description="[Admin] Remove force-sub channel"),
        BotCommand(command="listchnl",     description="[Admin] List force-sub channels"),
        BotCommand(command="fsub_mode",    description="[Admin] Toggle force-sub"),
        BotCommand(command="dlt_time",     description="[Admin] Set auto-delete timer"),
        BotCommand(command="setcaption",   description="[Admin] Set caption template"),
        BotCommand(command="help",         description="Help"),
        BotCommand(command="about",        description="About"),
    ])


async def on_startup(bot: Bot, **kwargs):
    try:
        await bot.get_chat(CHANNEL_ID)
        test = await bot.send_message(CHANNEL_ID, "✅ Startup check")
        await bot.delete_message(CHANNEL_ID, test.message_id)
    except Exception as e:
        logger.critical(f"DB channel error: {e}")
        sys.exit(1)

    await set_commands(bot)
    me   = await bot.get_me()
    mode = "Webhook" if WEBHOOK else "Polling"
    logger.info(f"Started: @{me.username} | {mode}")
    try:
        await bot.send_message(OWNER_ID, f"<b>✅ Bot started!</b>\n@{me.username} | <b>{mode}</b>")
    except Exception:
        pass


async def on_shutdown(bot: Bot, **kwargs):
    await bot.delete_webhook(drop_pending_updates=True)


def build_dp() -> Dispatcher:
    dp = Dispatcher()
    # Order matters — more specific handlers first
    dp.include_router(start_router)    # /start, file delivery, fsub gate
    dp.include_router(panel_router)    # /panel — must be before misc to catch panel input
    dp.include_router(links_router)    # /genlink + auto-genlink
    dp.include_router(batch_router)    # /batch /custom_batch /pro_batch /done /cancel
    dp.include_router(admin_router)    # ban/unban/timer/broadcast
    dp.include_router(fsub_router)     # force-sub commands + events
    dp.include_router(caption_router)  # /setcaption /getcaption /delcaption
    dp.include_router(logs_router)     # /logs
    dp.include_router(misc_router)     # /help /about /stats /uptime + reply guard
    return dp


async def run_webhook(bot: Bot, dp: Dispatcher):
    if not WEBHOOK_URL:
        logger.critical("WEBHOOK=True but WEBHOOK_URL not set!")
        sys.exit(1)

    full_url = f"{WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}"
    await bot.set_webhook(url=full_url, drop_pending_updates=True,
                          allowed_updates=dp.resolve_used_update_types())

    app = web.Application()
    app.router.add_get("/", lambda _: web.Response(text="AlisaFile Bot ✅"))
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info(f"Webhook on port {PORT} — {full_url}")
    await asyncio.Event().wait()


async def run_polling(bot: Bot, dp: Dispatcher):
    await bot.delete_webhook(drop_pending_updates=True)
    app = web.Application()
    app.router.add_get("/", lambda _: web.Response(text="AlisaFile Bot ✅ (polling)"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info(f"Health check on port {PORT}")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def main():
    CosmicBotz.init()
    bot = Bot(token=TG_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp  = build_dp()

    dp.startup.register(on_startup)
    if WEBHOOK:
        dp.shutdown.register(on_shutdown)

    if WEBHOOK:
        await run_webhook(bot, dp)
    else:
        await run_polling(bot, dp)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped.")
