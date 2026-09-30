from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import db
from services.force_subscribe import ForceSubscribeService
from states.states import BotStates
from keyboards.user import get_cancel_keyboard
from utils.cleanup import cleanup_user_temp

router = Router()

@router.callback_query(F.data == "check_force_sub")
async def cb_check_force_sub(callback: CallbackQuery, bot):
    user_id = callback.from_user.id
    is_joined, link = await ForceSubscribeService.is_user_subscribed(bot, user_id)

    if is_joined:
        await callback.answer("✅ Thank you for joining! Access granted.", show_alert=True)
        await callback.message.edit_text(
            "🎉 <b>MEMBERSHIP VERIFIED!</b>\n\n"
            "You now have full access to the bot features.\n"
            "Use /thum to edit thumbnails or /cap to edit captions."
        )
    else:
        await callback.answer("❌ You have not joined the channel yet. Please join and try again.", show_alert=True)

@router.message(Command("cancel"))
@router.callback_query(F.data == "btn_cancel")
async def handle_cancel(event: Message | CallbackQuery, state: FSMContext):
    user_id = event.from_user.id

    await state.clear()
    await state.set_state(BotStates.IDLE)
    cleanup_user_temp(user_id)

    msg_text = (
        "❌ <b>OPERATION CANCELLED</b>\n"
        "You can start a new operation whenever you want."
    )

    if isinstance(event, CallbackQuery):
        await event.answer("Operation cancelled.")
        await event.message.edit_text(msg_text)
    else:
        await event.answer(msg_text)
