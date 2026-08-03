import os
import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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

# Lightweight Health Check HTTP Server for Render Web Services
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - Swiggy Buzz Bot is Live")

    def log_message(self, format, *args):
        return # Quiet health check logs

def run_health_server():
    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Health check server listening on port {port}")
    server.serve_forever()

async def post_init(application):
    logger.info("Initializing database...")
    await database.init_db()
    logger.info("Database initialized successfully.")

def main():
    if not BOT_TOKEN or "YOUR_TELEGRAM_BOT_TOKEN" in BOT_TOKEN:
        logger.error("Error: BOT_TOKEN is missing or invalid in .env file.")
        return

    # If running on Render as a Web Service, start Health Check HTTP server on PORT
    port_env = os.getenv("PORT")
    if port_env:
        threading.Thread(target=run_health_server, daemon=True).start()

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
