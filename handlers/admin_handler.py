from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from config import ADMIN_IDS
import database

WAITING_RESTRICT_ID, WAITING_UNRESTRICT_ID, WAITING_BROADCAST_TEXT, WAITING_BULK_LINKS = range(10, 14)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def get_admin_keyboard():
    bot_active = await database.get_setting("bot_active", "1")
    links_enabled = await database.get_setting("links_enabled", "1")

    bot_active_text = "🟢 Bot: ACTIVE" if bot_active == "1" else "🔴 Bot: MAINTENANCE"
    links_text = "🟢 50 Links: ALLOWED" if links_enabled == "1" else "🔴 50 Links: PAUSED"

    keyboard = [
        [
            InlineKeyboardButton(bot_active_text, callback_data="admin_toggle_bot"),
            InlineKeyboardButton(links_text, callback_data="admin_toggle_links")
        ],
        [
            InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
            InlineKeyboardButton("👥 Manage Users", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton("🔗 View Links Panel", callback_data="admin_links_1"),
            InlineKeyboardButton("📥 Bulk Add Links", callback_data="admin_bulk_links_prompt")
        ],
        [
            InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast_prompt"),
            InlineKeyboardButton("🚫 Restrict User ID", callback_data="admin_restrict_prompt")
        ],
        [
            InlineKeyboardButton("✅ Unrestrict User ID", callback_data="admin_unrestrict_prompt"),
            InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="admin_refresh")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("🚫 Unauthorized access.")
        return

    reply_markup = await get_admin_keyboard()
    await update.message.reply_text(
        "🛠️ *Swiggy Bot Admin Dashboard*\n\n"
        "Control bot functions, toggle 50 links requests, view users & link statistics below:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    if not is_admin(user.id):
        await query.answer("Unauthorized", show_alert=True)
        return

    data = query.data
    await query.answer()

    if data == "admin_toggle_bot":
        curr = await database.get_setting("bot_active", "1")
        new_val = "0" if curr == "1" else "1"
        await database.set_setting("bot_active", new_val)
        reply_markup = await get_admin_keyboard()
        status_str = "MAINTENANCE" if new_val == "0" else "ACTIVE"
        await query.edit_message_text(f"✅ Bot status updated to *{status_str}*", reply_markup=reply_markup, parse_mode="Markdown")

    elif data == "admin_toggle_links":
        curr = await database.get_setting("links_enabled", "1")
        new_val = "0" if curr == "1" else "1"
        await database.set_setting("links_enabled", new_val)
        reply_markup = await get_admin_keyboard()
        status_str = "PAUSED (Users will get 'We are working on it')" if new_val == "0" else "ALLOWED"
        await query.edit_message_text(f"✅ 50 Links requests updated to *{status_str}*", reply_markup=reply_markup, parse_mode="Markdown")

    elif data == "admin_refresh":
        reply_markup = await get_admin_keyboard()
        await query.edit_message_text("🔄 Dashboard refreshed.", reply_markup=reply_markup)

    elif data == "admin_stats":
        stats = await database.get_stats()
        text = (
            "📊 *Bot Statistics Overview*\n\n"
            f"👤 *Total Users Registered:* {stats['total_users']}\n"
            f"🔗 *Total Links in DB:* {stats['total_links']}\n"
            f"⚡ *Active Links (<50 views):* {stats['active_links']}\n"
            f"🚀 *Total Link Distributions Made:* {stats['total_distributions']}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_refresh")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin_users":
        users = await database.get_all_users()
        if not users:
            text = "👥 No users found in database."
        else:
            lines = ["👥 *Registered Users List:*\n"]
            for u in users[:25]: # Limit preview
                status = "🚫 Restricted" if u["is_restricted"] == 1 else "✅ Active"
                uname = f"@{u['username']}" if u["username"] else u["first_name"]
                lines.append(f"• ID: `{u['user_id']}` | {uname} | Name: {u['swiggy_name']} | Status: {status}")
            if len(users) > 25:
                lines.append(f"\n_Showing 25 of {len(users)} total users._")
            text = "\n".join(lines)

        keyboard = [[InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_refresh")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin_links_"):
        page = int(data.split("_")[2])
        per_page = 50
        links, total_count = await database.get_all_links_paginated(page=page, per_page=per_page)
        
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        
        if not links:
            text = "🔗 No links registered in database yet."
            nav_buttons = []
        else:
            lines = [f"🔗 *Database Links Panel (Page {page}/{total_pages} - Total: {total_count})*\n"]
            for idx, l in enumerate(links, start=(page-1)*per_page + 1):
                cnt = l["received_count"]
                lines.append(f"{idx}. ID `{l['id']}` | User: `{l['user_id']}` | *{l['swiggy_name']}*\n   🔗 {l['swiggy_link']}\n   📊 Distributed: *{cnt}/50 times*")
            text = "\n".join(lines)

            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_links_{page-1}"))
            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_links_{page+1}"))

        keyboard = []
        if nav_buttons:
            keyboard.append(nav_buttons)
        keyboard.append([InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_refresh")])

        # Send link list in messages if text length exceeds Telegram limit
        if len(text) > 4000:
            text = text[:3900] + "\n\n_...truncated due to length limit_"
            
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown", disable_web_page_preview=True)

    elif data == "admin_restrict_prompt":
        await query.edit_message_text("🚫 Please type the *Telegram User ID* you want to restrict/ban:", parse_mode="Markdown")
        return WAITING_RESTRICT_ID

    elif data == "admin_unrestrict_prompt":
        await query.edit_message_text("✅ Please type the *Telegram User ID* you want to unrestrict/unban:", parse_mode="Markdown")
        return WAITING_UNRESTRICT_ID

    elif data == "admin_broadcast_prompt":
        await query.edit_message_text("📢 Send the message you want to broadcast to ALL registered users:", parse_mode="Markdown")
        return WAITING_BROADCAST_TEXT

    elif data == "admin_bulk_links_prompt":
        await query.edit_message_text(
            "📥 *Bulk Add Swiggy Links*\n\n"
            "Aap multiple links ek saath submit kar sakte hain.\n"
            "Links ko comma (`,`) se alag (separate) karke send karein:\n\n"
            "📌 *Example:*\n"
            "`https://swiggy.com/link1, https://swiggy.com/link2, https://swiggy.com/link3`\n\n"
            "Kripya links type karke send karein:",
            parse_mode="Markdown"
        )
        return WAITING_BULK_LINKS

async def handle_restrict_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("⚠️ Invalid User ID. Must be numbers only. Try again:")
        return WAITING_RESTRICT_ID

    target_id = int(text)
    await database.restrict_user(target_id, 1)
    reply_markup = await get_admin_keyboard()
    await update.message.reply_text(f"🚫 User ID `{target_id}` has been RESTRICTED.", reply_markup=reply_markup, parse_mode="Markdown")
    return ConversationHandler.END

async def handle_unrestrict_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("⚠️ Invalid User ID. Must be numbers only. Try again:")
        return WAITING_UNRESTRICT_ID

    target_id = int(text)
    await database.restrict_user(target_id, 0)
    reply_markup = await get_admin_keyboard()
    await update.message.reply_text(f"✅ User ID `{target_id}` has been UNRESTRICTED.", reply_markup=reply_markup, parse_mode="Markdown")
    return ConversationHandler.END

async def handle_broadcast_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broadcast_msg = update.message.text.strip()
    users = await database.get_all_users()

    await update.message.reply_text(f"⏳ Broadcasting message to {len(users)} users...")
    
    success_count = 0
    fail_count = 0

    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u["user_id"],
                text=f"📢 *Announcement from Admin:*\n\n{broadcast_msg}",
                parse_mode="Markdown"
            )
            success_count += 1
        except Exception:
            fail_count += 1

    reply_markup = await get_admin_keyboard()
    await update.message.reply_text(
        f"✅ *Broadcast Finished!*\n\n"
        f"• Sent Successfully: {success_count}\n"
        f"• Failed (Blocked/Deleted): {fail_count}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def handle_bulk_links_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text.strip()
    admin_id = update.effective_user.id

    # Split by comma (,) and newlines (\n)
    raw_list = raw_text.replace("\n", ",").split(",")
    links = [item.strip() for item in raw_list if item.strip()]

    if not links:
        await update.message.reply_text("⚠️ Kripya valid Swiggy links send karein (comma `,` se separate karke):")
        return WAITING_BULK_LINKS

    await update.message.reply_text(f"⏳ Processing {len(links)} links...")
    added_count, dup_count, invalid_count = await database.add_bulk_links(links, admin_id)

    reply_markup = await get_admin_keyboard()
    await update.message.reply_text(
        f"✅ *Bulk Links Upload Complete!*\n\n"
        f"• 📥 Successfully Added: *{added_count}*\n"
        f"• ⚠️ Skipped (Duplicates): *{dup_count}*\n"
        f"• 🚫 Skipped (Invalid Format): *{invalid_count}*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

def get_admin_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("admin", admin_command),
            CallbackQueryHandler(admin_callback)
        ],
        states={
            WAITING_RESTRICT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_restrict_input)],
            WAITING_UNRESTRICT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unrestrict_input)],
            WAITING_BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_input)],
            WAITING_BULK_LINKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bulk_links_input)],
        },
        fallbacks=[CommandHandler("admin", admin_command)],
        per_message=False
    )
