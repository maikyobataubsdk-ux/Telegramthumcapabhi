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
from utils.logger import logger
from config import config

router = Router()

BOT_START_TIME = time.time()

async def admin_filter(event: Message | CallbackQuery) -> bool:
    user_id = event.from_user.id
    return await db.is_admin(user_id)

router.message.filter(admin_filter)
router.callback_query.filter(admin_filter)

# --- Admin Main Commands ---

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(BotStates.IDLE)
    await message.answer("🛠 **ADMIN PANEL**", reply_markup=get_admin_panel_keyboard())

@router.callback_query(F.data == "admin_panel_main")
async def cb_admin_panel_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(BotStates.IDLE)
    await callback.message.edit_text("🛠 **ADMIN PANEL**", reply_markup=get_admin_panel_keyboard())
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
        "📊 **BOT STATISTICS & SYSTEM METRICS**\n\n"
        f"🌐 **Database Mode:** `{stats['db_mode']}`\n"
        f"⏱ **Uptime:** `{uptime}`\n\n"
        f"👥 **Total Users:** `{stats['total_users']}`\n"
        f"⚡ **Active Users (24h):** `{stats['active_users_24h']}`\n"
        f"🚫 **Banned Users:** `{stats['banned_users']}`\n\n"
        f"🎥 **Total Videos Processed:** `{stats['videos_processed']}`\n"
        f"🖼 **Total Thumbnail Edits:** `{stats['thumbnail_edits']}`\n"
        f"📝 **Total Caption Edits:** `{stats['caption_edits']}`\n\n"
        f"📅 **Today's Activity:**\n"
        f"  • Videos: `{stats['today_videos']}`\n"
        f"  • Thumbnails: `{stats['today_thumbnail_edits']}`\n"
        f"  • Captions: `{stats['today_caption_edits']}`\n\n"
        f"💻 **System Load:**\n"
        f"  • CPU: `{metrics['cpu_usage']}%` ({metrics['cpu_model']})\n"
        f"  • RAM: `{metrics['ram_used_mb']}MB / {metrics['ram_total_mb']}MB ({metrics['ram_percent']}%)` \n"
        f"  • Disk: `{metrics['disk_used_gb']}GB / {metrics['disk_total_gb']}GB ({metrics['disk_percent']}%)`"
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
    msg = "📢 **BROADCAST**\n\nPlease send the message or media you want to broadcast to all users.\nUse /cancel to abort."
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
        f"✅ **BROADCAST COMPLETED**\n\n"
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
            await event.answer(f"🚫 User `{user_id}` has been banned.")
            return

    await state.set_state(BotStates.ADMIN_BAN_USER)
    msg = "🚫 **BAN USER**\nSend the User ID you want to ban:"
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
    await message.answer(f"🚫 User `{user_id}` has been banned.", reply_markup=get_admin_back_keyboard())

@router.message(Command("unban"))
@router.callback_query(F.data == "admin_unban")
async def handle_unban_prompt(event: Message | CallbackQuery, state: FSMContext):
    if isinstance(event, Message):
        args = event.text.split(maxsplit=1)
        if len(args) > 1 and args[1].isdigit():
            user_id = int(args[1])
            await db.unban_user(user_id)
            await event.answer(f"✅ User `{user_id}` has been unbanned.")
            return

    await state.set_state(BotStates.ADMIN_UNBAN_USER)
    msg = "✅ **UNBAN USER**\nSend the User ID you want to unban:"
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
    await message.answer(f"✅ User `{user_id}` has been unbanned.", reply_markup=get_admin_back_keyboard())

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
        f"👤 **USER INFO**\n\n"
        f"🆔 **ID:** `{u['user_id']}`\n"
        f"👤 **Name:** {u['first_name']} {u.get('last_name') or ''}\n"
        f"🏷 **Username:** @{u['username'] if u.get('username') else 'N/A'}\n"
        f"📅 **Joined:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(u.get('joined_at', 0)))}\n"
        f"⚡ **Last Active:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(u.get('last_active', 0)))}\n"
        f"🎥 **Videos Processed:** `{u.get('videos_processed', 0)}`\n"
        f"🖼 **Thumbnail Edits:** `{u.get('thumbnail_edits', 0)}`\n"
        f"📝 **Caption Edits:** `{u.get('caption_edits', 0)}`\n"
        f"📌 **Status:** {status_str}"
    )
    await message.answer(text)

@router.message(Command("users"))
@router.callback_query(F.data == "admin_users")
async def handle_users_list(event: Message | CallbackQuery):
    all_users = await db.get_all_users()
    banned = await db.get_banned_users()
    text = (
        f"👥 **USERS SUMMARY**\n\n"
        f"Total Registered Users: `{len(all_users)}` \n"
        f"Total Banned Users: `{len(banned)}`"
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
        "🔐 **CONFIGURE FORCE SUBSCRIBE**\n\n"
        "Please send the target Channel ID (e.g. `-1001234567890`) followed by the Invite Link in this format:\n"
        "`CHANNEL_ID|INVITE_LINK`\n\n"
        "Example:\n"
        "`-1001234567890|https://t.me/example`"
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
        await message.answer("⚠️ Invalid format! Must be `CHANNEL_ID|INVITE_LINK`.")
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
        f"✅ **FORCE SUBSCRIBE ENABLED**\n\n"
        f"Channel ID: `{channel_id}`\n"
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

    msg = "✅ **Force Subscribe ENABLED**" if new_state else "❌ **Force Subscribe DISABLED**"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(msg, reply_markup=get_admin_back_keyboard())
        await event.answer()
    else:
        await event.answer(msg)

@router.message(Command("fsstatus"))
@router.callback_query(F.data in ["admin_fs_menu", "admin_fs_status"])
async def handle_fsstatus(event: Message | CallbackQuery):
    settings = await db.get_settings()
    fs_enabled = settings.get("force_subscribe", False)
    channel = settings.get("force_subscribe_channel", "Not Set")
    link = settings.get("force_subscribe_link", "Not Set")

    text = (
        f"🔐 **FORCE SUBSCRIBE STATUS**\n\n"
        f"Status: `{'Active' if fs_enabled else 'Disabled'}`\n"
        f"Channel ID: `{channel}`\n"
        f"Invite Link: `{link}`"
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

    msg = "🛠 **Maintenance Mode ENABLED**" if new_state else "✅ **Maintenance Mode DISABLED**"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(msg, reply_markup=get_admin_back_keyboard())
        await event.answer()
    else:
        await event.answer(msg)

# --- Logs & Settings & Restart & Migrate ---

@router.message(Command("logs"))
@router.callback_query(F.data == "admin_logs")
async def handle_logs(event: Message | CallbackQuery):
    text = "📋 **LOGS**\nSystem logs are written to standard output. Everything is functioning normally."
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
        f"⚙️ **SYSTEM SETTINGS**\n\n"
        f"• DB Mode: `{db.db_mode()}`\n"
        f"• Maintenance: `{settings.get('maintenance', False)}` \n"
        f"• Force Subscribe: `{settings.get('force_subscribe', False)}` \n"
        f"• Max Concurrent Jobs: `{config.MAX_CONCURRENT_JOBS}`"
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
        await status_msg.edit_text(f"✅ **MIGRATION SUCCESSFUL**\n\n{res['message']}")
    else:
        await status_msg.edit_text(f"❌ **MIGRATION FAILED**\n\n{res['message']}")
