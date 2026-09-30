import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from utils.logger import logger

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit_seconds: float = 1.0):
        super().__init__()
        self.limit_seconds = limit_seconds
        self.user_timestamps: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id:
            now = time.time()
            last_time = self.user_timestamps.get(user_id, 0)
            if now - last_time < self.limit_seconds:
                if isinstance(event, CallbackQuery):
                    await event.answer("⚠️ Please slow down!", show_alert=True)
                elif isinstance(event, Message):
                    await event.answer("⚠️ Please wait a moment before sending another request.")
                return
            self.user_timestamps[user_id] = now

        return await handler(event, data)
