from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from config import OWNER_ID
from database.database import CosmicBotz


class IsOwner(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        uid = event.from_user.id if event.from_user else 0
        return uid == OWNER_ID


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        uid = event.from_user.id if event.from_user else 0
        if uid == OWNER_ID:
            return True
        return await CosmicBotz.admin_exist(uid)


class IsNotBanned(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        uid = event.from_user.id if event.from_user else 0
        return not await CosmicBotz.ban_user_exist(uid)


is_owner      = IsOwner()
is_admin      = IsAdmin()
is_not_banned = IsNotBanned()
