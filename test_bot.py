import asyncio
import os
import shutil
import unittest
from database import Database, db
from aiogram.types import Message, CallbackQuery
from services.caption import CaptionService
from handlers.start import get_start_text, get_help_text, ABOUT_TEXT
from handlers.admin import admin_filter
from services.video import VideoService
from services.thumbnail import ThumbnailService
from services.force_subscribe import ForceSubscribeService
from utils.cleanup import generate_session_id, get_user_temp_dir, cleanup_user_temp, cleanup_path
from utils.helpers import format_time, get_system_metrics
from config import config
from PIL import Image

class TestSystem(unittest.IsolatedAsyncioTestCase):

    async def test_database_fallback(self):
        test_db = Database(json_filepath="temp/test_db.json")
        await test_db.connect()
        self.assertEqual(test_db.db_mode(), "JSON Fallback")

        await test_db.add_or_update_user(999, "john_doe", "John", "Doe")
        user = await test_db.get_user(999)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "john_doe")

        # Test ban/unban
        await test_db.ban_user(999)
        self.assertTrue(await test_db.is_banned(999))
        await test_db.unban_user(999)
        self.assertFalse(await test_db.is_banned(999))

        # Test stats
        await test_db.increment_stats(999, "thumbnail_edits", 2)
        stats = await test_db.get_stats()
        self.assertEqual(stats["thumbnail_edits"], 2)

        cleanup_path("temp/test_db.json")

    async def test_caption_service(self):
        self.assertTrue(CaptionService.validate_caption("Hello World"))
        self.assertFalse(CaptionService.validate_caption("a" * 1025))
        self.assertEqual(CaptionService.format_caption("  Test Caption  "), "Test Caption")

    async def test_cleanup_and_temp(self):
        session_id = generate_session_id()
        temp_dir = get_user_temp_dir(111, session_id)
        self.assertTrue(os.path.exists(temp_dir))

        test_file = os.path.join(temp_dir, "dummy.txt")
        with open(test_file, "w") as f:
            f.write("hello")

        self.assertTrue(os.path.exists(test_file))
        cleanup_user_temp(111)
        self.assertFalse(os.path.exists(temp_dir))

    async def test_system_helpers(self):
        metrics = get_system_metrics()
        self.assertIn("cpu_usage", metrics)
        self.assertIn("ram_used_mb", metrics)
        self.assertIn("disk_used_gb", metrics)

        time_str = format_time(3665)
        self.assertEqual(time_str, "1h 1m 5s")

    async def test_start_help_about_formatting(self):
        class DummyUser:
            full_name = "Alex Smith"
            first_name = "Alex"
            username = "alexsmith"
            id = 12345678

        user = DummyUser()
        start_txt = get_start_text("Alex Smith")
        self.assertIn("Starkeditbot", start_txt)

        help_txt = get_help_text(user)
        self.assertIn("🎯 Hᴇʟᴘ Cᴇɴᴛᴇʀ", help_txt)
        self.assertIn("Alex Smith", help_txt)
        self.assertIn("@alexsmith", help_txt)
        self.assertIn("12345678", help_txt)

        self.assertIn("https://t.me/the_Jarvis_bots", ABOUT_TEXT)
        self.assertIn("jarvis", ABOUT_TEXT)

    async def test_admin_filter_for_normal_users(self):
        class DummyUser:
            def __init__(self, user_id):
                self.id = user_id

        class DummyMessage:
            def __init__(self, user_id, text=""):
                self.from_user = DummyUser(user_id)
                self.text = text
                self.caption = None
                self.answered = False

            async def answer(self, *args, **kwargs):
                self.answered = True

        # Ensure test database doesn't mark 777777 as admin
        test_db = Database(json_filepath="temp/test_admin_db.json")
        await test_db.connect()

        original_owner = config.OWNER_ID
        original_admins = list(config.ADMIN_IDS)
        config.OWNER_ID = 123456789
        config.ADMIN_IDS = [123456789]
        try:
            # Inject test_db into database.py temporarily for test
            import database
            orig_db = database.db
            database.db = test_db

            # Non-admin user sending regular message or video
            msg_regular = DummyMessage(user_id=777777, text="Hello bot")
            res_regular = await admin_filter(msg_regular)
            self.assertFalse(res_regular)
            self.assertFalse(msg_regular.answered)

            # Non-admin user trying admin command
            msg_admin = DummyMessage(user_id=777777, text="/admin")
            res_admin = await admin_filter(msg_admin)
            self.assertFalse(res_admin)
            self.assertTrue(msg_admin.answered)
        finally:
            config.OWNER_ID = original_owner
            config.ADMIN_IDS = original_admins
            database.db = orig_db
            cleanup_path("temp/test_admin_db.json")

    async def test_thumbnail_service_processing(self):
        # Create a mock photo download and optimization test
        os.makedirs("temp/test_thumb", exist_ok=True)
        raw_path = "temp/test_thumb/sample.jpg"
        dest_path = "temp/test_thumb/mock.jpg"

        # Create a test image
        img = Image.new("RGB", (500, 500), color="blue")
        img.save(raw_path, format="JPEG")

        class MockBot:
            async def download(self, photo, destination):
                shutil.copyfile(raw_path, destination)

        success = await ThumbnailService.download_thumbnail(MockBot(), None, dest_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(dest_path))

        with Image.open(dest_path) as processed_img:
            self.assertLessEqual(processed_img.width, 320)
            self.assertLessEqual(processed_img.height, 320)

        cleanup_path("temp/test_thumb")

if __name__ == "__main__":
    unittest.main()
