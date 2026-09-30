import os
import json
import asyncio
import time
from typing import Dict, Any, List, Optional
import aiofiles
from utils.logger import logger
from config import config

class Database:
    """
    Database Abstraction Layer supporting MongoDB with automatic JSON fallback.
    If MONGO_URI is not provided or connection fails, uses data/database.json.
    """
    def __init__(self, json_filepath: str = "data/database.json"):
        self.json_filepath = json_filepath
        self.use_mongo = False
        self.mongo_client = None
        self.db = None
        self._json_lock = asyncio.Lock()

        # In-memory database state for JSON mode
        self._json_data: Dict[str, Any] = {
            "users": {},
            "admins": [config.OWNER_ID] if config.OWNER_ID else [],
            "banned_users": [],
            "settings": {
                "force_subscribe": False,
                "force_subscribe_channel": None,
                "force_subscribe_link": None,
                "maintenance": False
            },
            "statistics": {
                "total_users": 0,
                "videos_processed": 0,
                "thumbnail_edits": 0,
                "caption_edits": 0,
                "daily_stats": {}
            }
        }

    async def connect(self):
        """Attempts connection to MongoDB; falls back to JSON if unavailable."""
        mongo_uri = config.MONGO_URI
        if mongo_uri:
            try:
                from motor.motor_asyncio import AsyncIOMotorClient
                logger.info("Attempting MongoDB connection...")
                self.mongo_client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=3000)
                # Test connection
                await self.mongo_client.admin.command('ping')
                self.db = self.mongo_client[config.DATABASE_NAME]
                self.use_mongo = True
                logger.info("Connected to MongoDB successfully!")
                return
            except Exception as e:
                logger.warning(f"MongoDB connection failed: {e}. Switching to JSON fallback.")
                self.use_mongo = False
                self.mongo_client = None
                self.db = None

        logger.info(f"Using JSON Database fallback ({self.json_filepath}).")
        await self._init_json_db()

    async def _init_json_db(self):
        """Initializes and loads the JSON database file asynchronously."""
        async with self._json_lock:
            os.makedirs(os.path.dirname(self.json_filepath), exist_ok=True)
            if os.path.exists(self.json_filepath):
                try:
                    async with aiofiles.open(self.json_filepath, mode='r', encoding='utf-8') as f:
                        content = await f.read()
                        if content.strip():
                            data = json.loads(content)
                            # Deep update
                            self._json_data["users"] = data.get("users", {})
                            self._json_data["admins"] = data.get("admins", [config.OWNER_ID] if config.OWNER_ID else [])
                            self._json_data["banned_users"] = data.get("banned_users", [])
                            self._json_data["settings"].update(data.get("settings", {}))
                            self._json_data["statistics"].update(data.get("statistics", {}))
                except Exception as e:
                    logger.error(f"Error loading JSON database: {e}. Reinitializing.")

            # Ensure OWNER_ID is in admins list
            if config.OWNER_ID and config.OWNER_ID not in self._json_data["admins"]:
                self._json_data["admins"].append(config.OWNER_ID)

            await self._save_json_db_unlocked()

    async def _save_json_db_unlocked(self):
        """Helper to save in-memory JSON data to file. Lock must be held by caller."""
        try:
            temp_file = f"{self.json_filepath}.tmp"
            async with aiofiles.open(temp_file, mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(self._json_data, indent=2, ensure_ascii=False))
            os.replace(temp_file, self.json_filepath)
        except Exception as e:
            logger.error(f"Failed to write JSON database: {e}")

    async def _save_json_db(self):
        """Thread/task safe save for JSON database."""
        async with self._json_lock:
            await self._save_json_db_unlocked()

    def db_mode(self) -> str:
        return "MongoDB" if self.use_mongo else "JSON Fallback"

    # --- User Management ---
    async def add_or_update_user(self, user_id: int, username: Optional[str], first_name: str, last_name: Optional[str] = None):
        user_str = str(user_id)
        now = int(time.time())

        if self.use_mongo:
            try:
                users_col = self.db.users
                existing = await users_col.find_one({"user_id": user_id})
                if not existing:
                    user_doc = {
                        "user_id": user_id,
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "joined_at": now,
                        "last_active": now,
                        "videos_processed": 0,
                        "thumbnail_edits": 0,
                        "caption_edits": 0
                    }
                    await users_col.insert_one(user_doc)
                    await self.db.stats.update_one(
                        {"_id": "global"},
                        {"$inc": {"total_users": 1}},
                        upsert=True
                    )
                else:
                    await users_col.update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "username": username,
                            "first_name": first_name,
                            "last_name": last_name,
                            "last_active": now
                        }}
                    )
                return
            except Exception as e:
                logger.error(f"MongoDB error in add_or_update_user: {e}. Switching to JSON.")
                self.use_mongo = False

        # JSON fallback logic
        async with self._json_lock:
            if user_str not in self._json_data["users"]:
                self._json_data["users"][user_str] = {
                    "user_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "joined_at": now,
                    "last_active": now,
                    "videos_processed": 0,
                    "thumbnail_edits": 0,
                    "caption_edits": 0
                }
                self._json_data["statistics"]["total_users"] = len(self._json_data["users"])
            else:
                u = self._json_data["users"][user_str]
                u["username"] = username
                u["first_name"] = first_name
                u["last_name"] = last_name
                u["last_active"] = now

            await self._save_json_db_unlocked()

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        if self.use_mongo:
            try:
                user = await self.db.users.find_one({"user_id": user_id}, {"_id": 0})
                return user
            except Exception as e:
                logger.error(f"MongoDB error in get_user: {e}. Switching to JSON.")
                self.use_mongo = False

        user_str = str(user_id)
        return self._json_data["users"].get(user_str)

    async def get_all_users(self) -> List[Dict[str, Any]]:
        if self.use_mongo:
            try:
                cursor = self.db.users.find({}, {"_id": 0})
                return await cursor.to_list(length=None)
            except Exception as e:
                logger.error(f"MongoDB error in get_all_users: {e}. Switching to JSON.")
                self.use_mongo = False

        return list(self._json_data["users"].values())

    # --- Ban Management ---
    async def ban_user(self, user_id: int) -> bool:
        if self.use_mongo:
            try:
                await self.db.banned.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)
                return True
            except Exception as e:
                logger.error(f"MongoDB error in ban_user: {e}. Switching to JSON.")
                self.use_mongo = False

        async with self._json_lock:
            if user_id not in self._json_data["banned_users"]:
                self._json_data["banned_users"].append(user_id)
                await self._save_json_db_unlocked()
        return True

    async def unban_user(self, user_id: int) -> bool:
        if self.use_mongo:
            try:
                await self.db.banned.delete_one({"user_id": user_id})
                return True
            except Exception as e:
                logger.error(f"MongoDB error in unban_user: {e}. Switching to JSON.")
                self.use_mongo = False

        async with self._json_lock:
            if user_id in self._json_data["banned_users"]:
                self._json_data["banned_users"].remove(user_id)
                await self._save_json_db_unlocked()
        return True

    async def is_banned(self, user_id: int) -> bool:
        if self.use_mongo:
            try:
                doc = await self.db.banned.find_one({"user_id": user_id})
                return doc is not None
            except Exception as e:
                logger.error(f"MongoDB error in is_banned: {e}. Switching to JSON.")
                self.use_mongo = False

        return user_id in self._json_data["banned_users"]

    async def get_banned_users(self) -> List[int]:
        if self.use_mongo:
            try:
                cursor = self.db.banned.find({}, {"_id": 0, "user_id": 1})
                docs = await cursor.to_list(length=None)
                return [d["user_id"] for d in docs]
            except Exception as e:
                logger.error(f"MongoDB error in get_banned_users: {e}. Switching to JSON.")
                self.use_mongo = False

        return list(self._json_data["banned_users"])

    # --- Admin Management ---
    async def is_admin(self, user_id: int) -> bool:
        if user_id == config.OWNER_ID or user_id in config.ADMIN_IDS:
            return True
        if self.use_mongo:
            try:
                doc = await self.db.admins.find_one({"user_id": user_id})
                return doc is not None
            except Exception as e:
                logger.error(f"MongoDB error in is_admin: {e}. Switching to JSON.")
                self.use_mongo = False

        return user_id in self._json_data.get("admins", [])

    # --- Settings Management ---
    async def get_settings(self) -> Dict[str, Any]:
        default_settings = {
            "force_subscribe": False,
            "force_subscribe_channel": None,
            "force_subscribe_link": None,
            "maintenance": False
        }
        if self.use_mongo:
            try:
                doc = await self.db.settings.find_one({"_id": "global"}, {"_id": 0})
                if doc:
                    default_settings.update(doc)
                return default_settings
            except Exception as e:
                logger.error(f"MongoDB error in get_settings: {e}. Switching to JSON.")
                self.use_mongo = False

        return self._json_data.get("settings", default_settings)

    async def update_settings(self, updates: Dict[str, Any]):
        if self.use_mongo:
            try:
                await self.db.settings.update_one({"_id": "global"}, {"$set": updates}, upsert=True)
                return
            except Exception as e:
                logger.error(f"MongoDB error in update_settings: {e}. Switching to JSON.")
                self.use_mongo = False

        async with self._json_lock:
            self._json_data["settings"].update(updates)
            await self._save_json_db_unlocked()

    # --- Statistics & Increments ---
    async def increment_stats(self, user_id: int, action_type: str, count: int = 1):
        """
        action_type: 'thumbnail_edits' or 'caption_edits'
        """
        today = time.strftime("%Y-%m-%d")
        if self.use_mongo:
            try:
                user_field = action_type
                await self.db.users.update_one(
                    {"user_id": user_id},
                    {"$inc": {user_field: count, "videos_processed": count}}
                )
                await self.db.stats.update_one(
                    {"_id": "global"},
                    {"$inc": {
                        user_field: count,
                        "videos_processed": count,
                        f"daily.{today}.{user_field}": count,
                        f"daily.{today}.videos_processed": count
                    }},
                    upsert=True
                )
                return
            except Exception as e:
                logger.error(f"MongoDB error in increment_stats: {e}. Switching to JSON.")
                self.use_mongo = False

        user_str = str(user_id)
        async with self._json_lock:
            if user_str in self._json_data["users"]:
                u = self._json_data["users"][user_str]
                u[action_type] = u.get(action_type, 0) + count
                u["videos_processed"] = u.get("videos_processed", 0) + count

            stats = self._json_data["statistics"]
            stats[action_type] = stats.get(action_type, 0) + count
            stats["videos_processed"] = stats.get("videos_processed", 0) + count

            daily = stats.setdefault("daily_stats", {}).setdefault(today, {
                "thumbnail_edits": 0,
                "caption_edits": 0,
                "videos_processed": 0
            })
            daily[action_type] = daily.get(action_type, 0) + count
            daily["videos_processed"] = daily.get("videos_processed", 0) + count

            await self._save_json_db_unlocked()

    async def get_stats(self) -> Dict[str, Any]:
        today = time.strftime("%Y-%m-%d")
        if self.use_mongo:
            try:
                st = await self.db.stats.find_one({"_id": "global"}, {"_id": 0}) or {}
                total_users = await self.db.users.count_documents({})
                banned_count = await self.db.banned.count_documents({})

                # Active users in last 24h
                twenty_four_hours_ago = int(time.time()) - 86400
                active_users = await self.db.users.count_documents({"last_active": {"$gte": twenty_four_hours_ago}})

                daily = st.get("daily", {}).get(today, {})

                return {
                    "total_users": total_users,
                    "active_users_24h": active_users,
                    "banned_users": banned_count,
                    "videos_processed": st.get("videos_processed", 0),
                    "thumbnail_edits": st.get("thumbnail_edits", 0),
                    "caption_edits": st.get("caption_edits", 0),
                    "today_videos": daily.get("videos_processed", 0),
                    "today_thumbnail_edits": daily.get("thumbnail_edits", 0),
                    "today_caption_edits": daily.get("caption_edits", 0),
                    "db_mode": "MongoDB"
                }
            except Exception as e:
                logger.error(f"MongoDB error in get_stats: {e}. Switching to JSON.")
                self.use_mongo = False

        users = self._json_data["users"]
        twenty_four_hours_ago = int(time.time()) - 86400
        active_users = sum(1 for u in users.values() if u.get("last_active", 0) >= twenty_four_hours_ago)
        daily = self._json_data["statistics"].get("daily_stats", {}).get(today, {})

        return {
            "total_users": len(users),
            "active_users_24h": active_users,
            "banned_users": len(self._json_data["banned_users"]),
            "videos_processed": self._json_data["statistics"].get("videos_processed", 0),
            "thumbnail_edits": self._json_data["statistics"].get("thumbnail_edits", 0),
            "caption_edits": self._json_data["statistics"].get("caption_edits", 0),
            "today_videos": daily.get("videos_processed", 0),
            "today_thumbnail_edits": daily.get("thumbnail_edits", 0),
            "today_caption_edits": daily.get("caption_edits", 0),
            "db_mode": "JSON Fallback"
        }

    # --- Migration Support ---
    async def migrate_json_to_mongo(self) -> Dict[str, Any]:
        """Safely transfers JSON database data to MongoDB if MongoDB is active."""
        if not self.use_mongo or not self.db:
            return {"success": False, "message": "MongoDB is not currently connected."}

        try:
            # Transfer users
            users = list(self._json_data["users"].values())
            if users:
                for u in users:
                    await self.db.users.update_one({"user_id": u["user_id"]}, {"$set": u}, upsert=True)

            # Transfer banned
            banned = self._json_data["banned_users"]
            for b_id in banned:
                await self.db.banned.update_one({"user_id": b_id}, {"$set": {"user_id": b_id}}, upsert=True)

            # Transfer settings
            settings = self._json_data["settings"]
            await self.db.settings.update_one({"_id": "global"}, {"$set": settings}, upsert=True)

            # Transfer stats
            stats = self._json_data["statistics"]
            await self.db.stats.update_one({"_id": "global"}, {"$set": {
                "videos_processed": stats.get("videos_processed", 0),
                "thumbnail_edits": stats.get("thumbnail_edits", 0),
                "caption_edits": stats.get("caption_edits", 0),
                "total_users": len(users)
            }}, upsert=True)

            return {
                "success": True,
                "message": f"Successfully migrated {len(users)} users, {len(banned)} banned entries, and system settings to MongoDB!"
            }
        except Exception as e:
            logger.error(f"Migration error: {e}")
            return {"success": False, "message": f"Migration error: {str(e)}"}

db = Database()
