import os
import shutil
from aiogram import Bot
from aiogram.types import PhotoSize
from utils.logger import logger

class ThumbnailService:
    @staticmethod
    async def download_thumbnail(bot: Bot, photo: PhotoSize, destination_path: str) -> bool:
        """Downloads photo sent by user to local destination path."""
        try:
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            await bot.download(photo, destination=destination_path)
            return os.path.exists(destination_path) and os.path.getsize(destination_path) > 0
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {e}")
            return False
