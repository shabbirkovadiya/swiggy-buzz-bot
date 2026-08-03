import re
from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
import database

WAITING_LINK, WAITING_NAME = range(2)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Check bot status
    bot_active = await database.get_setting("bot_active", "1")
    if bot_active == "0":
        await update.message.reply_text("🚧 *Bot Maintenance Mode*: Bot filhal maintenance me hai. Kripya kuch samay baad try karein.", parse_mode="Markdown")
        return ConversationHandler.END

    # Check user restriction
    user_db = await database.get_user(user.id)
    if user_db and user_db["is_restricted"] == 1:
        await update.message.reply_text("🚫 Aapka account restricted hai. Aap bot use nahi kar sakte.")
        return ConversationHandler.END

    # Check if user already uploaded a link
    if await database.user_has_link(user.id):
        await update.message.reply_text(
            "✅ *Aapki link pehle se recorded hai!*\n\nType `/links` to get 50 links.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    welcome_text = (
        "👋 *Welcome to Swiggy Buzz Bot!*\n\n"
        "🔗 *Upload your Swiggy Buzz link here*\n\n"
        "⚠️ *Nice Note:* _Agar aap roj logo ko buzz back kr sake to hi bot use kre._\n\n"
        "Kripya apni Swiggy Buzz link niche send karein:"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")
    return WAITING_LINK

async def handle_link_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # Basic URL / Swiggy link validation
    if not (text.startswith("http://") or text.startswith("https://")) or "swiggy" not in text.lower():
        await update.message.reply_text(
            "⚠️ Kripya valid *Swiggy Buzz link* send karein (must start with http:// or https:// and contain swiggy):\n\n"
            "📌 _Note: Agar aap roj logo ko buzz back kr sake to hi bot use kre._",
            parse_mode="Markdown"
        )
        return WAITING_LINK

    # Check duplicate link in DB
    if await database.link_exists(text):
        await update.message.reply_text(
            "⚠️ *Duplicate Link!* Yeh link database me pehle se registered hai.\n"
            "Kripya apni unique link send karein:"
        )
        return WAITING_LINK

    context.user_data["swiggy_link"] = text
    await update.message.reply_text(
        "👍 Link received!\n\nAb apna *Swiggy Name* type karke send karein:",
        parse_mode="Markdown"
    )
    return WAITING_NAME

async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    swiggy_name = update.message.text.strip()
    swiggy_link = context.user_data.get("swiggy_link")
    user = update.effective_user

    if not swiggy_link:
        await update.message.reply_text("Kuch error hua. Kripya `/start` type karke firse try karein.", parse_mode="Markdown")
        return ConversationHandler.END

    if len(swiggy_name) < 2:
        await update.message.reply_text("Kripya valid Swiggy Name send karein:")
        return WAITING_NAME

    # Save to database
    await database.register_user_and_link(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        swiggy_name=swiggy_name,
        swiggy_link=swiggy_link
    )

    await update.message.reply_text(
        "🎉 *Your link is recorded successfully!*\n\nType `/links` for 50 links.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Process cancelled. Type `/start` whenever you want to register.")
    return ConversationHandler.END

def get_start_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            WAITING_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link_input)],
            WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
