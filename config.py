import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    MONGO_URI: str = os.getenv("MONGO_URI", "").strip()
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "thumbnail_editor")

    # OWNER_ID can be a single int or comma-separated list
    _owner_id_raw = os.getenv("OWNER_ID", "0")
    try:
        OWNER_ID: int = int(_owner_id_raw.split(",")[0].strip()) if _owner_id_raw else 0
        ADMIN_IDS: list[int] = [int(x.strip()) for x in _owner_id_raw.split(",") if x.strip().isdigit()]
    except Exception:
        OWNER_ID = 0
        ADMIN_IDS = []

    _log_channel = os.getenv("LOG_CHANNEL_ID", "")
    LOG_CHANNEL_ID: int | None = int(_log_channel.strip()) if _log_channel.strip().lstrip("-").isdigit() else None

    START_IMAGE_URL: str = os.getenv("START_IMAGE_URL", "").strip()
    OFFICIAL_CHANNEL: str = os.getenv("OFFICIAL_CHANNEL", "https://t.me/example")
    SUPPORT_LINK: str = os.getenv("SUPPORT_LINK", "https://t.me/example")

    try:
        MAX_CONCURRENT_JOBS: int = int(os.getenv("MAX_CONCURRENT_JOBS", "2"))
    except ValueError:
        MAX_CONCURRENT_JOBS = 2

config = Config()
