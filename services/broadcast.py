import asyncio
from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest
from database import db
from utils.logger import logger

class BroadcastService:
    @staticmethod
    async def broadcast_message(bot: Bot, message: Message, progress_msg: Message = None) -> dict:
        """
        Broadcasts message to all users in database with FloodWait handling.
        """
        users = await db.get_all_users()
        total = len(users)
        successful = 0
        failed = 0
        blocked = 0

        logger.info(f"Starting broadcast to {total} users...")

        for index, user in enumerate(users):
            user_id = user["user_id"]
            try:
                await message.copy_to(chat_id=user_id)
                successful += 1
            except TelegramRetryAfter as e:
                logger.warning(f"FloodWait hit during broadcast: sleeping for {e.retry_after}s")
                await asyncio.sleep(e.retry_after)
                try:
                    await message.copy_to(chat_id=user_id)
                    successful += 1
                except Exception:
                    failed += 1
            except TelegramForbiddenError:
                blocked += 1
            except TelegramBadRequest as e:
                failed += 1
            except Exception as e:
                failed += 1

            # Update progress message periodically
            if progress_msg and (index + 1) % 15 == 0:
                try:
                    await progress_msg.edit_text(
                        f"📢 **BROADCAST IN PROGRESS**\n\n"
                        f"Progress: {index + 1}/{total}\n"
                        f"✅ Sent: {successful}\n"
                        f"❌ Failed: {failed}\n"
                        f"🚫 Blocked: {blocked}"
                    )
                except Exception:
                    pass

            await asyncio.sleep(0.05)  # Rate limiting safety delay

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "blocked": blocked
        }
