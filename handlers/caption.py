import os
import asyncio
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import db
from states.states import BotStates
from keyboards.user import get_cancel_keyboard
from services.caption import CaptionService
from services.video import VideoService
from handlers.thumbnail import check_user_eligibility, semaphore
from utils.cleanup import generate_session_id, get_user_temp_dir, cleanup_path
from utils.logger import logger

router = Router()

@router.message(Command("cap"))
async def cmd_cap(message: Message, state: FSMContext, bot):
    user = message.from_user
    if not await check_user_eligibility(user.id, message, bot):
        return

    session_id = generate_session_id()
    temp_dir = get_user_temp_dir(user.id, session_id)

    await state.clear()
    await state.set_state(BotStates.CAP_WAITING_VIDEO)
    await state.update_data(
        session_id=session_id,
        temp_dir=temp_dir,
        video=None,
        new_caption=None
    )

    await message.answer(
        "📝 <b>CAPTION EDITOR</b>\n"
        "Please send the video whose caption you want to change.",
        reply_markup=get_cancel_keyboard()
    )

@router.message(BotStates.CAP_WAITING_VIDEO, F.video)
async def process_cap_video(message: Message, state: FSMContext):
    video_data = {
        "file_id": message.video.file_id,
        "file_name": message.video.file_name or "video.mp4",
        "duration": message.video.duration,
        "width": message.video.width,
        "height": message.video.height
    }

    await state.update_data(video=video_data)
    await state.set_state(BotStates.CAP_WAITING_CAPTION)

    await message.answer(
        "🎬 <b>VIDEO RECEIVED</b>\n"
        "Now send the new caption.\n"
        "Support text, emoji, line breaks, and Telegram-supported formatting where appropriate.",
        reply_markup=get_cancel_keyboard()
    )

@router.message(BotStates.CAP_WAITING_VIDEO, ~F.text.startswith("/"))
async def invalid_cap_video(message: Message):
    await message.answer("⚠️ Please send a valid video file.", reply_markup=get_cancel_keyboard())

@router.message(BotStates.CAP_WAITING_CAPTION, F.text & ~F.text.startswith("/"))
async def process_cap_text(message: Message, state: FSMContext):
    new_caption = message.text
    if not CaptionService.validate_caption(new_caption):
        await message.answer("⚠️ Caption is too long (max 1024 chars). Please send a shorter caption.")
        return

    formatted_caption = CaptionService.format_caption(new_caption)
    await state.update_data(new_caption=formatted_caption)

    await message.answer(
        "✅ <b>CAPTION RECEIVED</b>\n"
        "Your caption has been saved.\n"
        "Send /done to generate the edited video.",
        reply_markup=get_cancel_keyboard()
    )

@router.message(BotStates.CAP_WAITING_CAPTION, Command("done"))
async def process_cap_done(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    video_info = data.get("video")
    new_caption = data.get("new_caption")
    temp_dir = data.get("temp_dir")
    user_id = message.from_user.id

    if not video_info:
        await message.answer("❌ Video is missing. Please restart with /cap.")
        return

    if new_caption is None:
        await message.answer("⚠️ Please send the new caption before sending /done.")
        return

    await state.set_state(BotStates.CAP_PROCESSING)
    status_msg = await message.answer("⏳ <b>PROCESSING</b>\nApplying your new caption...")

    try:
        async with semaphore:
            # Resend video by file_id with new caption directly for optimal performance and quality
            await bot.send_video(
                chat_id=message.chat.id,
                video=video_info["file_id"],
                duration=video_info["duration"],
                width=video_info["width"],
                height=video_info["height"],
                caption=new_caption
            )

            await db.increment_stats(user_id, "caption_edits", 1)

        await status_msg.edit_text("✅ <b>PROCESSING COMPLETE</b>\nYour video with the new caption has been delivered!")

    except Exception as e:
        logger.error(f"Error processing caption update for user {user_id}: {e}")
        await status_msg.edit_text("❌ Failed to process video caption. Please try again.")
    finally:
        await state.clear()
        await state.set_state(BotStates.IDLE)
        cleanup_path(temp_dir)
