from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from database import db
from keyboards.user import get_start_keyboard, get_back_keyboard
from config import config
from states.states import BotStates
from utils.cleanup import cleanup_user_temp

router = Router()

START_TEXT = (
    "🎬 **VIDEO EDITOR BOT**\n\n"
    "Welcome to the advanced Telegram Video Editor.\n\n"
    "✨ **Features:**\n"
    "• Change video thumbnails\n"
    "• Change video captions\n"
    "• Process multiple videos\n"
    "• Fast processing\n"
    "• Simple interface\n"
    "• Automatic cleanup"
)

ABOUT_TEXT = (
    "ℹ️ **ABOUT**\n\n"
    "🎬 **Thumbnail & Caption Editor**\n"
    "A Telegram-based video editing utility.\n\n"
    "**Features:**\n"
    "🖼 Thumbnail Editor\n"
    "📝 Caption Editor\n"
    "🎥 Multiple Video Support\n"
    "⚡ Fast Processing\n"
    "🛡 Secure Sessions\n"
    "🧹 Automatic Cleanup\n\n"
    "Made with ❤️"
)

HELP_TEXT = (
    "HELP\n\n"
    "🖼 **THUMBNAIL**\n"
    "/thum\n"
    "Send your thumbnail, then send your videos. When finished, use /done.\n\n"
    "📝 **CAPTION**\n"
    "/cap\n"
    "Send your video, then send the new caption. Use /done to finish.\n\n"
    "/cancel\n"
    "Cancel the current operation."
)

async def _edit_or_caption(callback: CallbackQuery, text: str, reply_markup):
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=reply_markup)
    else:
        await callback.message.edit_text(text=text, reply_markup=reply_markup)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = message.from_user
    await db.add_or_update_user(user.id, user.username, user.first_name, user.last_name)

    # Reset FSM and cleanup temporary session
    await state.clear()
    await state.set_state(BotStates.IDLE)
    cleanup_user_temp(user.id)

    # Check maintenance
    settings = await db.get_settings()
    if settings.get("maintenance", False) and not await db.is_admin(user.id):
        await message.answer("🛠 **MAINTENANCE MODE**\nThe bot is currently under maintenance.\nPlease try again later.")
        return

    if config.START_IMAGE_URL:
        try:
            await message.answer_photo(
                photo=config.START_IMAGE_URL,
                caption=START_TEXT,
                reply_markup=get_start_keyboard()
            )
            return
        except Exception:
            pass

    await message.answer(START_TEXT, reply_markup=get_start_keyboard())

@router.callback_query(F.data == "nav_about")
async def cb_about(callback: CallbackQuery):
    await _edit_or_caption(callback, ABOUT_TEXT, get_back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "nav_help")
async def cb_help(callback: CallbackQuery):
    await _edit_or_caption(callback, HELP_TEXT, get_back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "nav_start")
async def cb_start_back(callback: CallbackQuery):
    await _edit_or_caption(callback, START_TEXT, get_start_keyboard())
    await callback.answer()
