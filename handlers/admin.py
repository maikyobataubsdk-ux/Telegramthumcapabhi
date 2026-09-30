import os
import sys
import time
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import db
from states.states import BotStates
from keyboards.admin import get_admin_panel_keyboard, get_admin_back_keyboard, get_fs_admin_keyboard
from services.broadcast import BroadcastService
from utils.helpers import format_time, get_system_metrics
from utils.logger import logger, LOG_FILE
from config import config

router = Router()

BOT_START_TIME = time.time()

async def admin_filter(event: Message | CallbackQuery) -> bool:
    user_id = event.from_user.id
    is_adm = await db.is_admin(user_id)
    if not is_adm:
        if isinstance(event, Message):
            await event.answer("❌ You are not authorized to use admin commands.")
        elif isinstance(event, CallbackQuery):
            await event.answer("❌ You are not authorized to perform this action.", show_alert=True)
        return False
    return True

router.message.filter(admin_filter)
router.callback_query.filter(admin_filter)

# --- Admin Main Commands ---

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(BotStates.IDLE)
    await message.answer("🛠 <b>ADMIN PANEL</b>", reply_markup=get_admin_panel_keyboard())

@router.callback_query(F.data == "admin_panel_main")
async def cb_admin_panel_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(BotStates.IDLE)
    await callback.message.edit_text("🛠 <b>ADMIN PANEL</b>", reply_markup=get_admin_panel_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_close")
async def cb_admin_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Admin panel closed.")

# --- Stats Command / Panel ---

@router.message(Command("stats"))
@router.callback_query(F.data == "admin_stats")
async def handle_stats(event: Message | CallbackQuery):
    stats = await db.get_stats()
    metrics = get_system_metrics()
    uptime = format_time(int(time.time() - BOT_START_TIME))

    text = (
        "📊 <b>BOT STATISTICS & SYSTEM METRICS</b>\n\n"
        f"🌐 <b>Database Mode:</b> <code>{stats['db_mode']}</code>\n"
        f"⏱ <b>Uptime:</b> <code>{uptime}</code>\n\n"
        f"👥 <b>Total Users:</b> <code>{stats['total_users']}</code>\n"
        f"⚡ <b>Active Users (24h):</b> <code>{stats['active_users_24h']}</code>\n"
        f"🚫 <b>Banned Users:</b> <code>{stats['banned_users']}</code>\n\n"
        f"🎥 <b>Total Videos Processed:</b> <code>{stats['videos_processed']}</code>\n"
        f"🖼 <b>Total Thumbnail Edits:</b> <code>{stats['thumbnail_edits']}</code>\n"
        f"📝 <b>Total Caption Edits:</b> <code>{stats['caption_edits']}</code>\n\n"
        f"📅 <b>Today's Activity:</b>\n"
        f"  • Videos: <code>{stats['today_videos']}</code>\n"
        f"  • Thumbnails: <code>{stats['today_thumbnail_edits']}</code>\n"
        f"  • Captions: <code>{stats['today_caption_edits']}</code>\n\n"
        f"💻 <b>System Load:</b>\n"
        f"  • CPU: <code>{metrics['cpu_usage']}%</code> ({metrics['cpu_model']})\n"
        f"  • RAM: <code>{metrics['ram_used_mb']}MB / {metrics['ram_total_mb']}MB ({metrics['ram_percent']}%)</code>\n"
        f"  • Disk: <code>{metrics['disk_used_gb']}GB / {metrics['disk_total_gb']}GB ({metrics['disk_percent']}%)</code>"
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=get_admin_back_keyboard())
        await event.answer()
    else:
        await event.answer(text)

# --- Broadcast Command / Panel ---

@router.message(Command("broadcast"))
@router.callback_query(F.data == "admin_broadcast")
async def handle_broadcast_start(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.ADMIN_BROADCAST)
    msg = "📢 <b>BROADCAST</b>\n\nPlease send the message or media you want to broadcast to all users.\nUse /cancel to abort."
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(msg)
        await event.answer()
    else:
        await event.answer(msg)

@router.message(BotStates.ADMIN_BROADCAST)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    status_msg = await message.answer("📢 Starting broadcast operation...")
    results = await BroadcastService.broadcast_message(bot, message, progress_msg=status_msg)

    await status_msg.edit_text(
        f"✅ <b>BROADCAST COMPLETED</b>\n\n"
        f"👥 Total Target: {results['total']}\n"
        f"✅ Successful: {results['successful']}\n"
        f"❌ Failed: {results['failed']}\n"
        f"🚫 Blocked Users: {results['blocked']}",
        reply_markup=get_admin_back_keyboard()
    )

# --- Ban / Unban ---

@router.message(Command("ban"))
@router.callback_query(F.data == "admin_ban")
async def handle_ban_prompt(event: Message | CallbackQuery, state: FSMContext):
    if isinstance(event, Message):
        args = event.text.split(maxsplit=1)
        if len(args) > 1 and args[1].isdigit():
            user_id = int(args[1])
            await db.ban_user(user_id)
            await event.answer(f"🚫 User <code>{user_id}</code> has been banned.")
            return

    await state.set_state(BotStates.ADMIN_BAN_USER)
    msg = "🚫 <b>BAN USER</b>\nSend the User ID you want to ban:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(msg)
        await event.answer()
    else:
        await event.answer(msg)

@router.message(BotStates.ADMIN_BAN_USER)
async def process_ban_input(message: Message, state: FSMContext):
    await state.clear()
    if not message.text.isdigit():
        await message.answer("⚠️ Invalid User ID. Operation cancelled.")
        return
    user_id = int(message.text)
    await db.ban_user(user_id)
    await message.answer(f"🚫 User <code>{user_id}</code> has been banned.", reply_markup=get_admin_back_keyboard())

@router.message(Command("unban"))
@router.callback_query(F.data == "admin_unban")
async def handle_unban_prompt(event: Message | CallbackQuery, state: FSMContext):
    if isinstance(event, Message):
        args = event.text.split(maxsplit=1)
        if len(args) > 1 and args[1].isdigit():
            user_id = int(args[1])
            await db.unban_user(user_id)
            await event.answer(f"✅ User <code>{user_id}</code> has been unbanned.")
            return

    await state.set_state(BotStates.ADMIN_UNBAN_USER)
    msg = "✅ <b>UNBAN USER</b>\nSend the User ID you want to unban:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(msg)
        await event.answer()
    else:
        await event.answer(msg)

@router.message(BotStates.ADMIN_UNBAN_USER)
async def process_unban_input(message: Message, state: FSMContext):
    await state.clear()
    if not message.text.isdigit():
        await message.answer("⚠️ Invalid User ID. Operation cancelled.")
        return
    user_id = int(message.text)
    await db.unban_user(user_id)
    await message.answer(f"✅ User <code>{user_id}</code> has been unbanned.", reply_markup=get_admin_back_keyboard())

# --- User Info / List ---

@router.message(Command("user"))
async def cmd_user_info(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("⚠️ Usage: /user USER_ID")
        return
    user_id = int(args[1])
    u = await db.get_user(user_id)
    if not u:
        await message.answer("❌ User not found in database.")
        return
    is_banned = await db.is_banned(user_id)
    status_str = "🚫 Banned" if is_banned else "✅ Active"

    text = (
        f"👤 <b>USER INFO</b>\n\n"
        f"🆔 <b>ID:</b> <code>{u['user_id']}</code>\n"
        f"👤 <b>Name:</b> {u['first_name']} {u.get('last_name') or ''}\n"
        f"🏷 <b>Username:</b> @{u['username'] if u.get('username') else 'N/A'}\n"
        f"📅 <b>Joined:</b> {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(u.get('joined_at', 0)))}\n"
        f"⚡ <b>Last Active:</b> {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(u.get('last_active', 0)))}\n"
        f"🎥 <b>Videos Processed:</b> <code>{u.get('videos_processed', 0)}</code>\n"
        f"🖼 <b>Thumbnail Edits:</b> <code>{u.get('thumbnail_edits', 0)}</code>\n"
        f"📝 <b>Caption Edits:</b> <code>{u.get('caption_edits', 0)}</code>\n"
        f"📌 <b>Status:</b> {status_str}"
    )
    await message.answer(text)

@router.message(Command("users"))
@router.callback_query(F.data == "admin_users")
async def handle_users_list(event: Message | CallbackQuery):
    all_users = await db.get_all_users()
    banned = await db.get_banned_users()
    text = (
        f"👥 <b>USERS SUMMARY</b>\n\n"
        f"Total Registered Users: <code>{len(all_users)}</code>\n"
        f"Total Banned Users: <code>{len(banned)}</code>"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=get_admin_back_keyboard())
        await event.answer()
    else:
        await event.answer(text)

# --- Force Subscribe System ---

@router.message(Command("setfs"))
@router.callback_query(F.data == "admin_fs_set")
async def handle_setfs(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.ADMIN_SET_FS)
    msg = (
        "🔐 <b>CONFIGURE FORCE SUBSCRIBE</b>\n\n"
        "Please send the target Channel ID (e.g. <code>-1001234567890</code>) followed by the Invite Link in this format:\n"
        "<code>CHANNEL_ID|INVITE_LINK</code>\n\n"
        "Example:\n"
        "<code>-1001234567890|https://t.me/example</code>"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(msg)
        await event.answer()
    else:
        await event.answer(msg)

@router.message(BotStates.ADMIN_SET_FS)
async def process_setfs(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    if "|" not in message.text:
        await message.answer("⚠️ Invalid format! Must be <code>CHANNEL_ID|INVITE_LINK</code>.")
        return

    parts = message.text.split("|", 1)
    channel_id_str = parts[0].strip()
    invite_link = parts[1].strip()

    try:
        channel_id = int(channel_id_str)
    except ValueError:
        await message.answer("⚠️ Invalid Channel ID format.")
        return

    # Verify bot membership
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
        if member.status not in ["administrator", "creator"]:
            await message.answer("⚠️ Warning: Bot is not an admin in this channel! Force Subscribe may fail.")
    except Exception as e:
        await message.answer(f"⚠️ Warning: Could not verify channel: {e}")

    await db.update_settings({
        "force_subscribe": True,
        "force_subscribe_channel": channel_id,
        "force_subscribe_link": invite_link
    })

    await message.answer(
        f"✅ <b>FORCE SUBSCRIBE ENABLED</b>\n\n"
        f"Channel ID: <code>{channel_id}</code>\n"
        f"Invite Link: {invite_link}",
        reply_markup=get_admin_back_keyboard()
    )

@router.message(Command("delfs"))
@router.callback_query(F.data == "admin_fs_toggle")
async def handle_delfs(event: Message | CallbackQuery):
    settings = await db.get_settings()
    current = settings.get("force_subscribe", False)
    new_state = not current
    await db.update_settings({"force_subscribe": new_state})

    msg = "✅ <b>Force Subscribe ENABLED</b>" if new_state else "❌ <b>Force Subscribe DISABLED</b>"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(msg, reply_markup=get_admin_back_keyboard())
        await event.answer()
    else:
        await event.answer(msg)

@router.message(Command("fsstatus"))
@router.callback_query(F.data.in_(["admin_fs_menu", "admin_fs_status"]))
async def handle_fsstatus(event: Message | CallbackQuery):
    settings = await db.get_settings()
    fs_enabled = settings.get("force_subscribe", False)
    channel = settings.get("force_subscribe_channel", "Not Set")
    link = settings.get("force_subscribe_link", "Not Set")

    text = (
        f"🔐 <b>FORCE SUBSCRIBE STATUS</b>\n\n"
        f"Status: <code>{'Active' if fs_enabled else 'Disabled'}</code>\n"
        f"Channel ID: <code>{channel}</code>\n"
        f"Invite Link: <code>{link}</code>"
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=get_fs_admin_keyboard(fs_enabled))
        await event.answer()
    else:
        await event.answer(text)

# --- Maintenance Mode ---

@router.message(Command("maintenance"))
@router.callback_query(F.data == "admin_maintenance")
async def handle_maintenance(event: Message | CallbackQuery):
    settings = await db.get_settings()
    current = settings.get("maintenance", False)
    new_state = not current
    await db.update_settings({"maintenance": new_state})

    msg = "🛠 <b>Maintenance Mode ENABLED</b>" if new_state else "✅ <b>Maintenance Mode DISABLED</b>"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(msg, reply_markup=get_admin_back_keyboard())
        await event.answer()
    else:
        await event.answer(msg)

# --- Logs & Settings & Restart & Migrate ---

@router.message(Command("logs"))
@router.callback_query(F.data == "admin_logs")
async def handle_logs(event: Message | CallbackQuery):
    log_content = "No logs recorded yet."
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                log_content = "".join(lines[-20:]) if lines else "Log file is empty."
        except Exception as e:
            log_content = f"Error reading log file: {e}"

    text = f"📋 <b>RECENT SYSTEM LOGS</b>\n\n<code>{log_content}</code>"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=get_admin_back_keyboard())
        await event.answer()
    else:
        await event.answer(text)

@router.message(Command("settings"))
@router.callback_query(F.data == "admin_settings")
async def handle_settings(event: Message | CallbackQuery):
    settings = await db.get_settings()
    text = (
        f"⚙️ <b>SYSTEM SETTINGS</b>\n\n"
        f"• DB Mode: <code>{db.db_mode()}</code>\n"
        f"• Maintenance: <code>{settings.get('maintenance', False)}</code>\n"
        f"• Force Subscribe: <code>{settings.get('force_subscribe', False)}</code>\n"
        f"• Max Concurrent Jobs: <code>{config.MAX_CONCURRENT_JOBS}</code>"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=get_admin_back_keyboard())
        await event.answer()
    else:
        await event.answer(text)

@router.message(Command("restart"))
async def handle_restart(message: Message):
    await message.answer("🔄 Restarting bot process...")
    sys.exit(0)

@router.message(Command("migrate"))
async def handle_migrate(message: Message):
    if message.from_user.id != config.OWNER_ID:
        await message.answer("❌ Owner only command.")
        return

    status_msg = await message.answer("⏳ Starting database migration from JSON to MongoDB...")
    res = await db.migrate_json_to_mongo()
    if res["success"]:
        await status_msg.edit_text(f"✅ <b>MIGRATION SUCCESSFUL</b>\n\n{res['message']}")
    else:
        await status_msg.edit_text(f"❌ <b>MIGRATION FAILED</b>\n\n{res['message']}")
