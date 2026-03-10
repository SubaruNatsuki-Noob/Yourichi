"""
CosmicBotz — async MongoDB singleton for AlisaFile Store Bot.
"""
import motor.motor_asyncio
import logging
from config import DB_URI, DB_NAME

logger = logging.getLogger(__name__)


class CosmicBotz:
    _client             = None
    _db                 = None
    _users              = None
    _admins             = None
    _banned             = None
    _fsub               = None
    _req_fsub_channels  = None
    _settings           = None  # universal KV store

    @classmethod
    def init(cls, uri: str = DB_URI, db_name: str = DB_NAME):
        cls._client            = motor.motor_asyncio.AsyncIOMotorClient(uri)
        cls._db                = cls._client[db_name]
        cls._users             = cls._db["users"]
        cls._admins            = cls._db["admins"]
        cls._banned            = cls._db["banned_user"]
        cls._fsub              = cls._db["fsub"]
        cls._req_fsub_channels = cls._db["request_forcesub_channel"]
        cls._settings          = cls._db["bot_settings"]
        logger.info(f"[CosmicBotz] Connected → {db_name}")

    # ── Generic KV ────────────────────────────────────────────────────────────
    @classmethod
    async def set_setting(cls, key: str, value):
        await cls._settings.update_one({"_id": key}, {"$set": {"value": value}}, upsert=True)

    @classmethod
    async def get_setting(cls, key: str, default=None):
        doc = await cls._settings.find_one({"_id": key})
        return doc["value"] if doc else default

    @classmethod
    async def del_setting(cls, key: str):
        await cls._settings.delete_one({"_id": key})

    # ── Users ──────────────────────────────────────────────────────────────────
    @classmethod
    async def present_user(cls, uid: int) -> bool:
        return bool(await cls._users.find_one({"_id": uid}))

    @classmethod
    async def add_user(cls, uid: int):
        if not await cls.present_user(uid):
            await cls._users.insert_one({"_id": uid})

    @classmethod
    async def full_userbase(cls) -> list:
        return [d["_id"] for d in await cls._users.find().to_list(None)]

    @classmethod
    async def del_user(cls, uid: int):
        await cls._users.delete_one({"_id": uid})

    # ── Admins ─────────────────────────────────────────────────────────────────
    @classmethod
    async def admin_exist(cls, uid: int) -> bool:
        return bool(await cls._admins.find_one({"_id": uid}))

    @classmethod
    async def add_admin(cls, uid: int):
        if not await cls.admin_exist(uid):
            await cls._admins.insert_one({"_id": uid})

    @classmethod
    async def del_admin(cls, uid: int):
        await cls._admins.delete_one({"_id": uid})

    @classmethod
    async def get_all_admins(cls) -> list:
        return [d["_id"] for d in await cls._admins.find().to_list(None)]

    # ── Banned ─────────────────────────────────────────────────────────────────
    @classmethod
    async def ban_user_exist(cls, uid: int) -> bool:
        return bool(await cls._banned.find_one({"_id": uid}))

    @classmethod
    async def add_ban_user(cls, uid: int):
        if not await cls.ban_user_exist(uid):
            await cls._banned.insert_one({"_id": uid})

    @classmethod
    async def del_ban_user(cls, uid: int):
        await cls._banned.delete_one({"_id": uid})

    @classmethod
    async def get_ban_users(cls) -> list:
        return [d["_id"] for d in await cls._banned.find().to_list(None)]

    # ── Settings shortcuts ─────────────────────────────────────────────────────
    @classmethod
    async def set_del_timer(cls, v: int):     await cls.set_setting("del_timer", v)
    @classmethod
    async def get_del_timer(cls) -> int:      return await cls.get_setting("del_timer", 0)

    @classmethod
    async def set_caption(cls, v: str):       await cls.set_setting("caption", v)
    @classmethod
    async def get_caption(cls):               return await cls.get_setting("caption", None)

    @classmethod
    async def set_batch_start(cls, v: dict):  await cls.set_setting("batch_start", v)
    @classmethod
    async def get_batch_start(cls):           return await cls.get_setting("batch_start", None)
    @classmethod
    async def del_batch_start(cls):           await cls.del_setting("batch_start")

    @classmethod
    async def set_batch_end(cls, v: dict):    await cls.set_setting("batch_end", v)
    @classmethod
    async def get_batch_end(cls):             return await cls.get_setting("batch_end", None)
    @classmethod
    async def del_batch_end(cls):             await cls.del_setting("batch_end")

    @classmethod
    async def set_log_channel(cls, v: int):   await cls.set_setting("log_channel", v)
    @classmethod
    async def get_log_channel(cls) -> int:    return await cls.get_setting("log_channel", 0)

    # ── FSub ───────────────────────────────────────────────────────────────────
    @classmethod
    async def channel_exist(cls, cid: int) -> bool:
        return bool(await cls._fsub.find_one({"_id": cid}))

    @classmethod
    async def add_channel(cls, cid: int):
        if not await cls.channel_exist(cid):
            await cls._fsub.insert_one({"_id": cid, "mode": "on"})

    @classmethod
    async def rem_channel(cls, cid: int):
        await cls._fsub.delete_one({"_id": cid})

    @classmethod
    async def show_channels(cls) -> list:
        return [d["_id"] for d in await cls._fsub.find().to_list(None)]

    @classmethod
    async def get_channel_mode(cls, cid: int) -> str:
        d = await cls._fsub.find_one({"_id": cid})
        return d.get("mode", "off") if d else "off"

    @classmethod
    async def set_channel_mode(cls, cid: int, mode: str):
        await cls._fsub.update_one({"_id": cid}, {"$set": {"mode": mode}}, upsert=True)

    # ── Request FSub ───────────────────────────────────────────────────────────
    @classmethod
    async def req_user(cls, cid: int, uid: int):
        try:
            await cls._req_fsub_channels.update_one(
                {"_id": int(cid)}, {"$addToSet": {"user_ids": int(uid)}}, upsert=True)
        except Exception as e:
            logger.error(f"req_user: {e}")

    @classmethod
    async def del_req_user(cls, cid: int, uid: int):
        await cls._req_fsub_channels.update_one({"_id": cid}, {"$pull": {"user_ids": uid}})

    @classmethod
    async def req_user_exist(cls, cid: int, uid: int) -> bool:
        try:
            return bool(await cls._req_fsub_channels.find_one({"_id": int(cid), "user_ids": int(uid)}))
        except Exception:
            return False

    @classmethod
    async def reqChannel_exist(cls, cid: int) -> bool:
        return cid in await cls.show_channels()

    @classmethod
    def req_fsub_col(cls):
        return cls._req_fsub_channels
