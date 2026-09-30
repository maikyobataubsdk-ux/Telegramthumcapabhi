import os
import shutil
import uuid
import aiofiles
from utils.logger import logger

def generate_session_id() -> str:
    return str(uuid.uuid4())[:8]

def get_user_temp_dir(user_id: int, session_id: str) -> str:
    path = os.path.join("temp", str(user_id), session_id)
    os.makedirs(path, exist_ok=True)
    return path

def cleanup_path(path: str):
    """Safely delete a file or directory tree."""
    if not path or not os.path.exists(path):
        return
    try:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            os.remove(path)
    except Exception as e:
        logger.error(f"Error cleaning up path {path}: {e}")

def cleanup_user_temp(user_id: int):
    """Deletes all temporary folders for a given user."""
    user_dir = os.path.join("temp", str(user_id))
    if os.path.exists(user_dir):
        cleanup_path(user_dir)
