from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Returns the inline admin control panel keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 Users", callback_data="admin_users"),
                InlineKeyboardButton(text="📊 Statistics", callback_data="admin_stats")
            ],
            [
                InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton(text="🚫 Ban", callback_data="admin_ban"),
                InlineKeyboardButton(text="✅ Unban", callback_data="admin_unban")
            ],
            [
                InlineKeyboardButton(text="🔐 Force Subscribe", callback_data="admin_fs_menu")
            ],
            [
                InlineKeyboardButton(text="🛠 Maintenance", callback_data="admin_maintenance")
            ],
            [
                InlineKeyboardButton(text="📋 Logs", callback_data="admin_logs"),
                InlineKeyboardButton(text="⚙️ Settings", callback_data="admin_settings")
            ],
            [
                InlineKeyboardButton(text="❌ Close Panel", callback_data="admin_close")
            ]
        ]
    )
    return keyboard

def get_fs_admin_keyboard(fs_enabled: bool) -> InlineKeyboardMarkup:
    """Returns Force Subscribe control buttons in Admin panel."""
    toggle_text = "❌ Disable FS" if fs_enabled else "✅ Enable FS"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚙️ Configure FS Channel", callback_data="admin_fs_set")
            ],
            [
                InlineKeyboardButton(text="📊 FS Status", callback_data="admin_fs_status"),
                InlineKeyboardButton(text=toggle_text, callback_data="admin_fs_toggle")
            ],
            [
                InlineKeyboardButton(text="⬅️ Back to Admin Panel", callback_data="admin_panel_main")
            ]
        ]
    )
    return keyboard

def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    """Returns back button to return to the main admin panel."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Back to Admin Panel", callback_data="admin_panel_main")
            ]
        ]
    )
    return keyboard
