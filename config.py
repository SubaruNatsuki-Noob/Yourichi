import os
import logging
from logging.handlers import RotatingFileHandler

# ─────────────────────────────────────────────────────────────────────────────
# BOT CREDENTIALS
# ─────────────────────────────────────────────────────────────────────────────
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
APP_ID       = int(os.environ.get("APP_ID",   "0"))
API_HASH     = os.environ.get("API_HASH",      "")

# ─────────────────────────────────────────────────────────────────────────────
# OWNER / ADMINS
# ─────────────────────────────────────────────────────────────────────────────
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
OWNER    = os.environ.get("OWNER", "")           # username without @

# ─────────────────────────────────────────────────────────────────────────────
# STORAGE CHANNEL  (DB channel — bot must be admin here)
# ─────────────────────────────────────────────────────────────────────────────
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────
DB_URI  = os.environ.get("DATABASE_URL",  "")
DB_NAME = os.environ.get("DATABASE_NAME", "AlisaFileBot")

# ─────────────────────────────────────────────────────────────────────────────
# WEB SERVER & WEBHOOK
# ─────────────────────────────────────────────────────────────────────────────
PORT = int(os.environ.get("PORT", "8080"))

# Set WEBHOOK=True  → Telegram pushes updates to your Render URL (recommended)
# Set WEBHOOK=False → Bot polls Telegram for updates (fallback / local dev)
WEBHOOK = os.environ.get("WEBHOOK", "True") == "True"

# Your Render public URL — e.g. https://your-app-name.onrender.com
# Required when WEBHOOK=True. Leave blank if using polling.
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

# Internal path Telegram will POST updates to (keep this secret-ish)
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook")

# ─────────────────────────────────────────────────────────────────────────────
# FORCE SUBSCRIBE
# ─────────────────────────────────────────────────────────────────────────────
FSUB_LINK_EXPIRY = int(os.environ.get("FSUB_LINK_EXPIRY", "60"))
BAN_SUPPORT      = os.environ.get("BAN_SUPPORT", "https://t.me/")

# ─────────────────────────────────────────────────────────────────────────────
# MEDIA / UI
# ─────────────────────────────────────────────────────────────────────────────
START_PIC              = os.environ.get("START_PIC",              "")
FORCE_PIC              = os.environ.get("FORCE_PIC",              "")
PROTECT_CONTENT        = os.environ.get("PROTECT_CONTENT",        "False") == "True"
DISABLE_CHANNEL_BUTTON = os.environ.get("DISABLE_CHANNEL_BUTTON", "False") == "True"

# ─────────────────────────────────────────────────────────────────────────────
# MESSAGES  (all original texts preserved)
# ─────────────────────────────────────────────────────────────────────────────
START_MSG = os.environ.get(
    "START_MESSAGE",
    "<b>ʜᴇʟʟᴏ {mention}\n\n"
    "<blockquote>ɪ ᴀᴍ ᴀ ꜰɪʟᴇ sᴛᴏʀᴇ ʙᴏᴛ. ɪ ᴄᴀɴ sᴛᴏʀᴇ ᴘʀɪᴠᴀᴛᴇ ꜰɪʟᴇs ɪɴ ᴀ "
    "sᴘᴇᴄɪꜰɪᴇᴅ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴏᴛʜᴇʀ ᴜsᴇʀs ᴄᴀɴ ᴀᴄᴄᴇss ᴛʜᴇᴍ ᴠɪᴀ ᴀ sᴘᴇᴄɪᴀʟ ʟɪɴᴋ.</blockquote></b>"
)

FORCE_MSG = os.environ.get(
    "FORCE_SUB_MESSAGE",
    "ʜᴇʟʟᴏ {mention}\n\n"
    "<b><blockquote>ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ(s) ᴀɴᴅ ᴛʜᴇɴ ᴄʟɪᴄᴋ 🔄 Rᴇʟᴏᴀᴅ "
    "ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ꜰɪʟᴇ.</blockquote></b>"
)

HELP_TXT = (
    "<b><blockquote>ᴛʜɪs ɪs ᴀ ꜰɪʟᴇ-sᴛᴏʀᴇ ʙᴏᴛ.\n\n"
    "❏ ᴄᴏᴍᴍᴀɴᴅs\n"
    "├ /start  — sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ\n"
    "├ /about  — ɪɴꜰᴏ\n"
    "└ /help   — ᴛʜɪs ᴍᴇɴᴜ\n\n"
    "sɪᴍᴘʟʏ ᴄʟɪᴄᴋ ᴀ ʟɪɴᴋ ᴀɴᴅ ᴊᴏɪɴ ᴛʜᴇ ʀᴇǫᴜɪʀᴇᴅ ᴄʜᴀɴɴᴇʟs "
    "ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ꜰɪʟᴇ.</blockquote></b>"
)

ABOUT_TXT = (
    "<b><blockquote>"
    "◈ ʙᴏᴛ: AlisaFile Store\n"
    "◈ ꜰʀᴀᴍᴇᴡᴏʀᴋ: Aiogram 3\n"
    "◈ ʟᴀɴɢᴜᴀɢᴇ: Python 3\n"
    "◈ ᴅᴇᴠᴇʟᴏᴘᴇʀ: @{OWNER}\n"
    "</blockquote></b>"
)

CMD_TXT = """<blockquote><b>» ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs:</b></blockquote>

<b>›› /dlt_time</b>        — sᴇᴛ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ
<b>›› /check_dlt_time</b>  — ᴄʜᴇᴄᴋ ᴄᴜʀʀᴇɴᴛ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ
<b>›› /dbroadcast</b>      — ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴏᴄᴜᴍᴇɴᴛ / ᴠɪᴅᴇᴏ
<b>›› /ban</b>             — ʙᴀɴ ᴀ ᴜꜱᴇʀ
<b>›› /unban</b>           — ᴜɴʙᴀɴ ᴀ ᴜꜱᴇʀ
<b>›› /banlist</b>         — ɢᴇᴛ ʟɪsᴛ ᴏꜰ ʙᴀɴɴᴇᴅ ᴜꜱᴇʀs
<b>›› /addchnl</b>         — ᴀᴅᴅ ꜰᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ
<b>›› /delchnl</b>         — ʀᴇᴍᴏᴠᴇ ꜰᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ
<b>›› /listchnl</b>        — ᴠɪᴇᴡ ᴀᴅᴅᴇᴅ ᴄʜᴀɴɴᴇʟs
<b>›› /fsub_mode</b>       — ᴛᴏɢɢʟᴇ ꜰᴏʀᴄᴇ sᴜʙ ᴍᴏᴅᴇ
<b>›› /pbroadcast</b>      — sᴇɴᴅ ᴘʜᴏᴛᴏ ᴛᴏ ᴀʟʟ ᴜꜱᴇʀs
<b>›› /add_admin</b>       — ᴀᴅᴅ ᴀɴ ᴀᴅᴍɪɴ
<b>›› /deladmin</b>        — ʀᴇᴍᴏᴠᴇ ᴀɴ ᴀᴅᴍɪɴ
<b>›› /admins</b>          — ɢᴇᴛ ʟɪsᴛ ᴏꜰ ᴀᴅᴍɪɴs
<b>›› /delreq</b>          — Rᴇᴍᴏᴠᴇ ʟᴇꜰᴛᴏᴠᴇʀ ɴᴏɴ-ʀᴇǫᴜᴇsᴛ ᴜsᴇʀs
<b>›› /genlink</b>         — ɢᴇɴᴇʀᴀᴛᴇ ʟɪɴᴋ ꜰᴏʀ ᴀ ꜰɪʟᴇ
<b>›› /batch</b>           — sᴛᴀʀᴛ ʙᴀᴛᴄʜ ᴜᴘʟᴏᴀᴅ sᴇssɪᴏɴ
<b>›› /custom_batch</b>    — ʟɪɴᴋ ʙʏ sᴘᴇᴄɪꜰɪᴄ ᴍsɢ IDs
<b>›› /done</b>            — ꜰɪɴɪsʜ ʙᴀᴛᴄʜ sᴇssɪᴏɴ
<b>›› /cancel</b>          — ᴀʙᴏʀᴛ ʙᴀᴛᴄʜ sᴇssɪᴏɴ
<b>›› /setcaption</b>      — sᴇᴛ ᴄᴀᴘᴛɪᴏɴ ᴛᴇᴍᴘʟᴀᴛᴇ
<b>›› /getcaption</b>      — ᴠɪᴇᴡ ᴄᴀᴘᴛɪᴏɴ ᴛᴇᴍᴘʟᴀᴛᴇ
<b>›› /delcaption</b>      — ʀᴇsᴇᴛ ᴄᴀᴘᴛɪᴏɴ
<b>›› /stats</b>           — ʙᴏᴛ sᴛᴀᴛs
<b>›› /uptime</b>          — ʙᴏᴛ ᴜᴘᴛɪᴍᴇ
"""

# Caption template — variables filled at file delivery time
# Supports: {title} {clean_title} {episode} {season} {quality} {extension}
CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", "<b>• {title}</b>")

BOT_STATS_TEXT  = "<b>BOT UPTIME</b>\n{uptime}"
USER_REPLY_TEXT = "ʙᴀᴋᴋᴀ! ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴍʏ sᴇɴᴘᴀɪ!!"

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
LOG_FILE_NAME = "alisafile.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler(LOG_FILE_NAME, maxBytes=50_000_000, backupCount=10),
        logging.StreamHandler(),
    ],
)
logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
