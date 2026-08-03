import os
import asyncio
import logging
import threading
import json
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN, ADMIN_IDS
import database
from handlers.start_handler import get_start_conversation_handler
from handlers.links_handler import get_links_handler
from handlers.admin_handler import get_admin_conversation_handler, admin_callback

# ── In-memory logs (last 200 entries each) ──────────────────────────────────
activity_logs = []   # {time, level, message}
error_logs    = []   # {time, message}
MAX_LOGS = 200

def _now_str():
    return datetime.datetime.now().strftime("%H:%M:%S")

def log_activity(message: str, level: str = "INFO"):
    activity_logs.append({"time": _now_str(), "level": level, "message": message})
    if len(activity_logs) > MAX_LOGS:
        activity_logs.pop(0)

def log_error(message: str):
    error_logs.append({"time": _now_str(), "message": message})
    if len(error_logs) > MAX_LOGS:
        error_logs.pop(0)
    log_activity(message, "ERROR")

# ── Logging setup ────────────────────────────────────────────────────────────
class PanelLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        level = record.levelname
        if level == "ERROR" or level == "CRITICAL":
            log_error(msg)
        else:
            log_activity(msg, level)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
panel_handler = PanelLogHandler()
panel_handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(panel_handler)

# ── CORS / helpers ───────────────────────────────────────────────────────────
def _json(handler, data, status=200):
    body = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)

def _auth_ok(handler) -> bool:
    secret = handler.headers.get("X-Secret", "")
    return secret.strip() in [str(aid) for aid in ADMIN_IDS]

# ── HTTP Server ──────────────────────────────────────────────────────────────
class AdminHandler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "X-Secret,Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        # UptimeRobot endpoint
        if path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK - Swiggy Buzz Bot is Live")
            return

        # Admin panel HTML
        if path == "/admin":
            html_path = os.path.join(os.path.dirname(__file__), "admin_panel.html")
            try:
                with open(html_path, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"admin_panel.html not found")
            return

        # ── Protected API endpoints ──
        if not _auth_ok(self):
            _json(self, {"error": "Unauthorized"}, 401)
            return

        if path == "/api/stats":
            asyncio.run_coroutine_threadsafe(self._send_stats(), _loop).result(timeout=10)
            return

        if path == "/api/logs":
            _json(self, {"logs": activity_logs})
            return

        if path == "/api/errors":
            _json(self, {"errors": error_logs})
            return

        if path == "/api/users":
            asyncio.run_coroutine_threadsafe(self._send_users(), _loop).result(timeout=10)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        if path == "/api/auth":
            code = str(body.get("code", "")).strip()
            if code in [str(aid) for aid in ADMIN_IDS]:
                _json(self, {"ok": True})
            else:
                _json(self, {"error": "Wrong code"}, 403)
            return

        self.send_response(404)
        self.end_headers()

    async def _send_stats(self):
        try:
            stats = await database.get_stats()
            _json(self, stats)
        except Exception as e:
            log_error(f"Stats fetch failed: {e}")
            _json(self, {"error": str(e)}, 500)

    async def _send_users(self):
        try:
            users = await database.get_all_users()
            result = []
            for u in users:
                result.append({
                    "user_id":    u["user_id"],
                    "username":   u["username"],
                    "first_name": u["first_name"],
                    "swiggy_name":u["swiggy_name"],
                    "is_restricted": u["is_restricted"],
                    "created_at": u["created_at"],
                })
            _json(self, {"users": result})
        except Exception as e:
            log_error(f"Users fetch failed: {e}")
            _json(self, {"error": str(e)}, 500)

    def log_message(self, format, *args):
        return  # suppress default access logs

# Global event loop reference
_loop: asyncio.AbstractEventLoop = None

def run_health_server():
    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), AdminHandler)
    logger.info(f"Admin server listening on port {port} → /admin")
    server.serve_forever()

async def post_init(application):
    global _loop
    _loop = asyncio.get_running_loop()
    logger.info("Initializing database...")
    await database.init_db()
    logger.info("Database initialized successfully.")
    log_activity("Bot started ✅", "SUCCESS")

def main():
    if not BOT_TOKEN or "YOUR_TELEGRAM_BOT_TOKEN" in BOT_TOKEN:
        logger.error("Error: BOT_TOKEN is missing or invalid in .env file.")
        return

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

    application.add_handler(get_start_conversation_handler())
    application.add_handler(get_links_handler())
    application.add_handler(get_admin_conversation_handler())
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))

    logger.info("Bot is polling for updates...")
    application.run_polling()

if __name__ == "__main__":
    main()
