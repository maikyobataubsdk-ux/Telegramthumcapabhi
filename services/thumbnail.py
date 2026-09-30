import os
import shutil
from PIL import Image
from aiogram import Bot
from aiogram.types import PhotoSize
from utils.logger import logger

class ThumbnailService:
    @staticmethod
    async def download_thumbnail(bot: Bot, photo: PhotoSize, destination_path: str) -> bool:
        """Downloads photo sent by user to local destination path and optimizes it for Telegram thumbnail specifications."""
        try:
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            temp_path = destination_path + ".raw"
            await bot.download(photo, destination=temp_path)

            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                return False

            # Process with PIL to guarantee valid Telegram JPEG thumbnail (max 320x320, RGB)
            with Image.open(temp_path) as img:
                img = img.convert("RGB")
                img.thumbnail((320, 320))
                img.save(destination_path, "JPEG", quality=85, optimize=True)

            if os.path.exists(temp_path):
                os.remove(temp_path)

            return os.path.exists(destination_path) and os.path.getsize(destination_path) > 0
        except Exception as e:
            logger.error(f"Error downloading or processing thumbnail: {e}")
            # Fallback if PIL processing fails
            if os.path.exists(destination_path + ".raw"):
                os.replace(destination_path + ".raw", destination_path)
            return os.path.exists(destination_path) and os.path.getsize(destination_path) > 0
