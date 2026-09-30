from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_force_sub_keyboard(channel_link: str) -> InlineKeyboardMarkup:
    """Returns the Force Subscribe prompt buttons."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Join Channel", url=channel_link)
            ],
            [
                InlineKeyboardButton(text="✅ Try Again", callback_data="check_force_sub")
            ]
        ]
    )
    return keyboard
