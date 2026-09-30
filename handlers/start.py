from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from database import db
from keyboards.user import get_start_keyboard, get_back_keyboard
from config import config
from states.states import BotStates
from utils.cleanup import cleanup_user_temp

router = Router()

def get_start_text(name: str) -> str:
    return (
        f"𝖧𝖾𝗒 {name}\n\n"
        "๏ 𝖸𝗈𝗎’𝗋𝖾 𝗍𝖺𝗅𝗄𝗂𝗇𝗀 𝗍𝗈 @Starkeditbot ✨!\n\n"
        "➻ 𝖠 𝗉𝗋𝖾𝗆𝗂𝗎𝗆, 𝗉𝗈𝗐𝖾𝗋𝗉𝖺𝖼𝗄𝖾𝖽 𝖳𝗁𝗎𝗆𝖻𝗇𝖺𝗂𝗅 𝖺𝗇𝖽 𝖢𝖺𝗉𝗍𝗂𝗈𝗇 𝖡𝗈𝗍.\n"
        "────────────────────\n"
        "๏ 𝖳𝗋𝗒 𝗛𝗲𝗹𝗽 𝗍𝗈 𝖽𝗂𝗌𝖼𝗈𝗏𝖾𝗋 𝖺𝗅𝗅 𝗍𝗁𝖾 𝖿ull 𝖼𝗈𝗆𝗆𝖺𝗇𝖽𝗌 𝖺𝗇𝖽 𝖿𝖾𝖺𝗍𝗎𝗋𝖾𝗌!"
    )

def get_help_text(user) -> str:
    name = user.full_name or user.first_name
    username = f"@{user.username}" if user.username else "N/A"
    userid = user.id
    return (
        "🎯 Hᴇʟᴘ Cᴇɴᴛᴇʀ\n\n"
        f"💫 Hᴇʏ {name}\n\n"
        "┏━━━━━━━━━━━━━━━━━━┓\n"
        "┃  ⚡ Sᴘᴇᴄɪᴀʟ Fᴇᴀᴛᴜʀᴇs  ┃\n"
        "┗━━━━━━━━━━━━━━━━━━┛\n\n"
        "🚀 Lɪɢʜᴛɴɪɴɢ Fᴀsᴛ - Iɴsᴛᴀɴᴛ ᴅᴇʟɪᴠᴇʀY\n"
        "🔒 Sᴜᴘᴇʀ Sᴇᴄᴜʀᴇ - Eɴᴄʀʏᴘᴛᴇᴅ\n"
        "⏰ 24/7 Oɴʟɪɴᴇ - Aʟᴡᴀʏs ᴀᴠᴀɪʟᴀʙʟᴇ\n\n"
        "┏━━━━━━━━━━━━━━━━━━┓\n"
        "┃  ⚠️ Rᴜʟᴇs & Rᴇǫᴜɪʀᴇᴍᴇɴᴛs  ┃\n"
        "┗━━━━━━━━━━━━━━━━━━┛\n\n"
        "❗ Jᴏɪɴ ALL ᴍᴇɴᴛɪᴏɴᴇᴅ ᴄʜᴀɴɴᴇʟs (ᴍᴀɴᴅᴀᴛᴏʀY)\n"
        "❗ Dᴏɴ'ᴛ ʟᴇᴀᴠᴇ ᴀғᴛᴇʀ ɢᴇᴛᴛɪɴɢ ᴛʜᴇ ғɪʟᴇ\n"
        "❗ Sᴛᴀʏ ᴀs ᴀ ᴍᴇᴍʙᴇʀ ғᴏʀ ғᴜᴛᴜʀᴇ ᴀᴄᴄᴇss\n"
        "✅ Fᴏʟʟᴏᴡ ʀᴜʟᴇs ғᴏʀ ᴜɴɪɴᴛᴇʀʀᴜᴘᴛᴇᴅ sᴇʀᴠɪCᴇ\n\n"
        "┏━━━━━━━━━━━━━━━━━━┓\n"
        "┃  👤 Yᴏᴜʀ Pʀᴏғɪʟᴇ  ┃\n"
        "┗━━━━━━━━━━━━━━━━━━┛\n\n"
        f"📛 Nᴀᴍᴇ: {name}\n"
        f"🔖 Usᴇʀɴᴀᴍᴇ: {username}\n"
        f"🆔 Usᴇʀ ID: {userid}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 Tɪᴘ: Usᴇ /start ᴛᴏ ɢᴏ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴍᴇɴᴜ"
    )

ABOUT_TEXT = (
    '◈ ᴄʀᴇᴀᴛᴏʀ: <a href="https://t.me/the_Jarvis_bots">jarvis</a>\n'
    '◈ ꜰᴏᴜɴᴅᴇʀ ᴏꜰ : <a href="https://t.me/the_Jarvis_bots">jarvis</a>\n'
    '◈ ᴅᴀᴛᴀʙᴀsᴇ: ᴍᴏɴɢᴏ ᴅʙ\n'
    '» ᴅᴇᴠᴇʟᴏᴘᴇʀ: <a href="https://t.me/the_Jarvis_bots">jarvis</a>'
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
        await message.answer("🛠 <b>MAINTENANCE MODE</b>\nThe bot is currently under maintenance.\nPlease try again later.")
        return

    start_text = get_start_text(user.full_name or user.first_name)

    if config.START_IMAGE_URL:
        try:
            await message.answer_photo(
                photo=config.START_IMAGE_URL,
                caption=start_text,
                reply_markup=get_start_keyboard()
            )
            return
        except Exception:
            pass

    await message.answer(start_text, reply_markup=get_start_keyboard())

@router.message(Command("help"))
async def cmd_help(message: Message):
    user = message.from_user
    help_text = get_help_text(user)
    await message.answer(help_text, reply_markup=get_back_keyboard())

@router.callback_query(F.data == "nav_about")
async def cb_about(callback: CallbackQuery):
    await _edit_or_caption(callback, ABOUT_TEXT, get_back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "nav_help")
async def cb_help(callback: CallbackQuery):
    help_text = get_help_text(callback.from_user)
    await _edit_or_caption(callback, help_text, get_back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "nav_start")
async def cb_start_back(callback: CallbackQuery):
    user = callback.from_user
    start_text = get_start_text(user.full_name or user.first_name)
    await _edit_or_caption(callback, start_text, get_start_keyboard())
    await callback.answer()
