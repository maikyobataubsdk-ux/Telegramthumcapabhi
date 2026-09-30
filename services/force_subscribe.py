from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from database import db
from utils.logger import logger

class ForceSubscribeService:
    @staticmethod
    async def is_user_subscribed(bot: Bot, user_id: int) -> tuple[bool, str | None]:
        """
        Checks if user is subscribed to the force subscribe channel if enabled.
        Returns (is_joined: bool, channel_link: str | None).
        """
        settings = await db.get_settings()
        if not settings.get("force_subscribe", False):
            return True, None

        channel_id = settings.get("force_subscribe_channel")
        channel_link = settings.get("force_subscribe_link")

        if not channel_id or not channel_link:
            return True, None

        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status in ["creator", "administrator", "member"]:
                return True, channel_link
            else:
                return False, channel_link
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logger.error(f"Force Subscribe check failed for channel {channel_id}: {e}")
            # If bot cannot check membership (e.g. not admin in channel), pass check to avoid blocking user permanently
            return True, channel_link
        except Exception as e:
            logger.error(f"Unexpected error in ForceSubscribeService: {e}")
            return True, channel_link
