import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from config import config
from database import db
from utils.logger import logger
from utils.rate_limit import RateLimitMiddleware

from handlers import start, thumbnail, caption, force_subscribe, admin

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="thum", description="Change video thumbnail"),
        BotCommand(command="cap", description="Change video caption"),
        BotCommand(command="help", description="Get help"),
        BotCommand(command="cancel", description="Cancel operation")
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is missing in environment variables. Exiting.")
        sys.exit(1)

    # Connect DB (MongoDB or JSON fallback)
    await db.connect()
    logger.info(f"Database initialized in {db.db_mode()} mode.")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )

    dp = Dispatcher()

    # Register Middlewares
    dp.message.middleware(RateLimitMiddleware(limit_seconds=0.8))
    dp.callback_query.middleware(RateLimitMiddleware(limit_seconds=0.5))

    # Register Routers
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(force_subscribe.router)
    dp.include_router(thumbnail.router)
    dp.include_router(caption.router)

    await setup_bot_commands(bot)

    logger.info("Bot starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
