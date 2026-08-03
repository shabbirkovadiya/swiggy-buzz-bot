# 🚀 Swiggy Buzz Telegram Bot

A complete, feature-rich Telegram Bot built in Python (`python-telegram-bot` v20+ async) and SQLite (`aiosqlite`) to manage Swiggy Buzz links, enforce distribution limits (max 50 users per link), restrict duplicates, provide 24-hour rate limiting, and offer an interactive Admin Panel.

---

## 📋 Features

1. **User Onboarding (`/start`)**:
   - Welcome message with disclaimer: *"Agar aap roj logo ko buzz back kr sake to hi bot use kre"*.
   - Prompts user to upload Swiggy Buzz link & Swiggy Name.
   - Validates link and prevents duplicate links in Database.
   - Ensures user's own link is never sent back to them.

2. **Link Distribution (`/links`)**:
   - Fetches 50 unique links per request.
   - **Distribution Cap**: Each link in DB is sent to a **maximum of 50 unique users** (`received_count <= 50`).
   - **Duplicate Prevention**: User never gets the same link twice.
   - **24-Hour Cooldown**: Enforces 24-hour waiting period before requesting the next batch of 50 links.
   - **Admin Toggle Check**: Displays `"We are working on it request after sometime"` if requests are paused by Admin.

3. **Interactive Admin Panel (`/admin`)**:
   - ⚡ **Bot Status Toggle**: Switch between Active & Maintenance Mode.
   - 🚫 **50 Links Request Switch**: Enable or pause 50 link requests across all users.
   - 👥 **Users Management**: View registered users, check status, and restrict/unrestrict user IDs.
   - 🔗 **Links Panel**: Paginated link view in 50-per-page chunks with view counters (`X/50 sent`).
   - 📊 **Bot Statistics**: Real-time stats on total users, total links, active links, and distributions.
   - 📢 **Broadcast Message**: Send announcement messages to all registered users.

---

## 🛠️ Requirements & Database

- **Language**: Python 3.10+
- **Database**: **SQLite3** (using `aiosqlite` - zero setup required, stored locally in `swiggy_bot.db`).
- **Dependencies**:
  - `python-telegram-bot>=20.7`
  - `aiosqlite>=0.19.0`
  - `python-dotenv>=1.0.0`

---

## ⚡ Setup & Installation

1. **Clone/Navigate to Project Directory**:
   ```bash
   cd "c:\Users\dell\Downloads\swiggy bot"
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment (`.env`)**:
   Open `.env` and set your Telegram Bot token and Admin User ID:
   ```env
   BOT_TOKEN=8828239744:AAHKaccXHIZDhydfk9Xws6sJxGg5CJCuZGU
   ADMIN_IDS=YOUR_TELEGRAM_USER_ID
   ```
   *(Get your Telegram User ID from `@userinfobot` on Telegram).*

4. **Run the Bot**:
   ```bash
   python bot.py
   ```

---

## 📁 Project Structure

```
swiggy bot/
├── .env                # Bot Token & Admin IDs
├── config.py           # Configuration loader
├── database.py         # Async SQLite DB queries & distribution engine
├── bot.py              # Main bot entry point
├── requirements.txt    # Required python packages
├── req.txt             # Setup & requirements guide
├── README.md           # Documentation
└── handlers/
    ├── __init__.py
    ├── start_handler.py# /start conversation & link submission
    ├── links_handler.py# /links 50-link engine & 24h limit check
    └── admin_handler.py# /admin panel & inline callback menus
```
