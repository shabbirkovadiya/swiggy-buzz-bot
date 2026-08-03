import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8828239744:AAHKaccXHIZDhydfk9Xws6sJxGg5CJCuZGU")

# Parse comma separated admin IDs
admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()]

DB_PATH = os.getenv("DB_PATH", "swiggy_bot.db")
MONGO_URI = os.getenv("MONGO_URI", "")  # Optional: For 100% Free MongoDB Atlas cloud DB
