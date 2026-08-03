import asyncio
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN
import database
from handlers.start_handler import get_start_conversation_handler
from handlers.links_handler import get_links_handler
from handlers.admin_handler import get_admin_conversation_handler, admin_callback

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def post_init(application):
    logger.info("Initializing database...")
    await database.init_db()
    logger.info("Database initialized successfully.")

def main():
    if not BOT_TOKEN or "YOUR_TELEGRAM_BOT_TOKEN" in BOT_TOKEN:
        logger.error("Error: BOT_TOKEN is missing or invalid in .env file.")
        return

    logger.info("Starting Swiggy Buzz Telegram Bot...")

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register Handlers
    application.add_handler(get_start_conversation_handler())
    application.add_handler(get_links_handler())
    application.add_handler(get_admin_conversation_handler())
    
    # Catch-all admin callback query handler for pagination & buttons outside conversation states
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))

    logger.info("Bot is polling for updates...")
    application.run_polling()

if __name__ == "__main__":
    main()
