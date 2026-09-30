import os
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import db
from states.states import BotStates
from keyboards.user import get_cancel_keyboard
from keyboards.force_subscribe import get_force_sub_keyboard
from services.force_subscribe import ForceSubscribeService
from services.video import VideoService
from services.thumbnail import ThumbnailService
from utils.cleanup import generate_session_id, get_user_temp_dir, cleanup_path, cleanup_user_temp
from utils.logger import logger
from config import config

router = Router()

# Shared processing semaphore
semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_JOBS)

async def check_user_eligibility(user_id: int, message: Message, bot) -> bool:
    # 1. Ban check
    if await db.is_banned(user_id):
        await message.answer("❌ You are banned from using this bot.")
        return False

    # 2. Maintenance check
    settings = await db.get_settings()
    if settings.get("maintenance", False) and not await db.is_admin(user_id):
        await message.answer("🛠 **MAINTENANCE MODE**\nThe bot is currently under maintenance.\nPlease try again later.")
        return False

    # 3. Force Subscribe check
    is_joined, link = await ForceSubscribeService.is_user_subscribed(bot, user_id)
    if not is_joined and link:
        await message.answer(
            "🔐 **JOIN REQUIRED**\n"
            "To use this bot, you must first join our required channel.\n"
            "👇 Join the channel and then verify your membership.",
            reply_markup=get_force_sub_keyboard(link)
        )
        return False

    return True

@router.message(Command("thum"))
async def cmd_thum(message: Message, state: FSMContext, bot):
    user = message.from_user
    if not await check_user_eligibility(user.id, message, bot):
        return

    # Initialize new session
    session_id = generate_session_id()
    temp_dir = get_user_temp_dir(user.id, session_id)

    await state.clear()
    await state.set_state(BotStates.THUMB_WAITING_PHOTO)
    await state.update_data(
        session_id=session_id,
        temp_dir=temp_dir,
        thumbnail_path=None,
        videos=[]
    )

    await message.answer(
        "🖼 **THUMBNAIL EDITOR**\n"
        "Please send the thumbnail photo you want to use.\n"
        "This thumbnail will be applied to all videos in this session.",
        reply_markup=get_cancel_keyboard()
    )

@router.message(BotStates.THUMB_WAITING_PHOTO, F.photo)
async def process_thumb_photo(message: Message, state: FSMContext, bot):
    user_id = message.from_user.id
    data = await state.get_data()
    temp_dir = data.get("temp_dir") or get_user_temp_dir(user_id, generate_session_id())

    photo = message.photo[-1]
    thumb_path = os.path.join(temp_dir, "custom_thumb.jpg")

    success = await ThumbnailService.download_thumbnail(bot, photo, thumb_path)
    if not success:
        await message.answer("❌ Failed to download thumbnail photo. Please try again.", reply_markup=get_cancel_keyboard())
        return

    await state.update_data(thumbnail_path=thumb_path)
    await state.set_state(BotStates.THUMB_WAITING_VIDEOS)

    await message.answer(
        "✅ **THUMBNAIL RECEIVED**\n"
        "Now send all the videos you want to edit.\n"
        "You can send multiple videos.\n"
        "When finished, send:\n/done",
        reply_markup=get_cancel_keyboard()
    )

@router.message(BotStates.THUMB_WAITING_PHOTO, ~F.text.startswith("/"))
async def invalid_thumb_photo(message: Message):
    await message.answer("⚠️ Please send a valid photo for the thumbnail.", reply_markup=get_cancel_keyboard())

@router.message(BotStates.THUMB_WAITING_VIDEOS, F.video)
async def process_thumb_video(message: Message, state: FSMContext):
    data = await state.get_data()
    videos = data.get("videos", [])

    videos.append({
        "file_id": message.video.file_id,
        "file_name": message.video.file_name or f"video_{len(videos)+1}.mp4",
        "duration": message.video.duration,
        "width": message.video.width,
        "height": message.video.height,
        "caption": message.caption or ""
    })

    await state.update_data(videos=videos)
    await message.answer(f"✅ Video #{len(videos)} added")

@router.message(BotStates.THUMB_WAITING_VIDEOS, Command("done"))
async def process_thumb_done(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    thumbnail_path = data.get("thumbnail_path")
    videos = data.get("videos", [])
    temp_dir = data.get("temp_dir")
    user_id = message.from_user.id

    if not thumbnail_path or not os.path.exists(thumbnail_path):
        await message.answer("❌ Thumbnail image is missing. Please restart with /thum.")
        return

    if not videos:
        await message.answer("⚠️ Please send at least one video before sending /done.")
        return

    await state.set_state(BotStates.THUMB_PROCESSING)
    status_msg = await message.answer(f"⏳ **PROCESSING**\nFound: {len(videos)} videos\nApplying your thumbnail...")

    total = len(videos)
    successful = 0
    failed = 0

    try:
        for idx, vid in enumerate(videos, start=1):
            async with semaphore:
                try:
                    in_video_path = os.path.join(temp_dir, f"input_{idx}.mp4")
                    out_video_path = os.path.join(temp_dir, f"output_{idx}.mp4")

                    # Download original video
                    file_info = await bot.get_file(vid["file_id"])
                    await bot.download_file(file_info.file_path, destination=in_video_path)

                    # Apply thumbnail
                    apply_ok = await VideoService.apply_thumbnail(in_video_path, thumbnail_path, out_video_path)

                    if apply_ok and os.path.exists(out_video_path):
                        # Extract metadata
                        meta = await VideoService.get_video_metadata(out_video_path)
                        duration = meta["duration"] or vid["duration"]
                        width = meta["width"] or vid["width"]
                        height = meta["height"] or vid["height"]

                        # Send edited video with original caption preserved
                        video_file = FSInputFile(out_video_path)
                        thumb_file = FSInputFile(thumbnail_path)

                        await bot.send_video(
                            chat_id=message.chat.id,
                            video=video_file,
                            thumbnail=thumb_file,
                            duration=duration,
                            width=width,
                            height=height,
                            caption=vid["caption"]
                        )
                        successful += 1
                        await db.increment_stats(user_id, "thumbnail_edits", 1)
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Error processing video #{idx} for user {user_id}: {e}")
                    failed += 1
                finally:
                    cleanup_path(os.path.join(temp_dir, f"input_{idx}.mp4"))
                    cleanup_path(os.path.join(temp_dir, f"output_{idx}.mp4"))

        await status_msg.edit_text(
            f"✅ **PROCESSING COMPLETE**\n\n"
            f"Total: {total}\n"
            f"✅ Successful: {successful}\n"
            f"❌ Failed: {failed}"
        )
    finally:
        await state.clear()
        await state.set_state(BotStates.IDLE)
        cleanup_path(temp_dir)
