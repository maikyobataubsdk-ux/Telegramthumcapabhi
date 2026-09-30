from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Returns Start UI keyboard with About and Help in one row."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="ℹ️ About", callback_data="nav_about"),
                InlineKeyboardButton(text="🆘 Help", callback_data="nav_help")
            ]
        ]
    )
    return keyboard

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Returns Back button keyboard for About/Help submenus."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Back", callback_data="nav_start")
            ]
        ]
    )
    return keyboard

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Returns Cancel button keyboard for active editing state."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Cancel", callback_data="btn_cancel")
            ]
        ]
    )
    return keyboard
