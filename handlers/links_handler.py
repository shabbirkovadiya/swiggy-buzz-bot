import datetime
import re
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import database

def escape_md(text: str) -> str:
    """Escape special Markdown v1 characters in a string to prevent parse errors."""
    # Escape characters that have special meaning in Telegram Markdown v1
    return re.sub(r'([_*`\[\]])', r'\\\1', text)

async def links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # 1. Check Bot Active Status
    bot_active = await database.get_setting("bot_active", "1")
    if bot_active == "0":
        await update.message.reply_text("🚧 *Bot Maintenance Mode*: Bot filhal maintenance me hai. Kripya kuch samay baad try karein.", parse_mode="Markdown")
        return

    # 2. Check Admin 50 Links Request Switch
    links_enabled = await database.get_setting("links_enabled", "1")
    if links_enabled == "0":
        await update.message.reply_text("We are working on it request after sometime")
        return

    # 3. Check User Restriction
    user_db = await database.get_user(user.id)
    if user_db and user_db.get("is_restricted", 0) == 1:
        await update.message.reply_text("🚫 Aapka account restricted hai. Aap 50 links request nahi kar sakte.")
        return

    # 3b. Check if admin has disabled link delivery for this specific user
    if user_db and user_db.get("can_receive_links", 1) == 0:
        await update.message.reply_text("⏳ Aapke liye links abhi available nahi hain. Kripya kuch samay baad try karein.")
        return

    # 4. Check if User Registered a Link
    if not await database.user_has_link(user.id):
        await update.message.reply_text(
            "⚠️ *Aapne abhi tak apni Swiggy link record nahi ki hai!*\n\n"
            "Pehle `/start` command click karke apni link upload karein, uske baad hi aap 50 links le sakte hain.",
            parse_mode="Markdown"
        )
        return

    # 5. Check 24-Hour Cooldown Limit
    last_req_str = user_db.get("last_links_request_at") if user_db else None
    now = datetime.datetime.now(datetime.timezone.utc)

    if last_req_str:
        try:
            last_req_dt = datetime.datetime.fromisoformat(last_req_str)
            # Ensure timezone awareness
            if last_req_dt.tzinfo is None:
                last_req_dt = last_req_dt.replace(tzinfo=datetime.timezone.utc)
            
            elapsed = (now - last_req_dt).total_seconds()
            twenty_four_hours = 24 * 3600

            if elapsed < twenty_four_hours:
                remaining_sec = twenty_four_hours - elapsed
                hours = int(remaining_sec // 3600)
                minutes = int((remaining_sec % 3600) // 60)
                
                await update.message.reply_text(
                    f"⏳ *24-Hour Limit Reached!*\n\n"
                    f"Aap 24 ghante me 50 links ek hi baar request kar sakte hain.\n"
                    f"Aap **{hours} ghante {minutes} mins** ke baad next 50 links request kar sakte hain.",
                    parse_mode="Markdown"
                )
                return
        except Exception as e:
            pass # Invalid timestamp format fallback

    # 6. Fetch Available Links (Max 50)
    links = await database.get_available_links_for_user(user.id, limit=50)

    if not links:
        await update.message.reply_text(
            "⚠️ *Abhi database me naye links available nahi hain.*\n\n"
            "Naye users ke join karne par dobara try karein!",
            parse_mode="Markdown"
        )
        return

    # 7. Record Distributions
    link_ids = [l["id"] for l in links]
    await database.record_link_distributions(user.id, link_ids)

    # 8. Send each link as a separate individual message
    total_fetched = len(links)
    await update.message.reply_text(
        f"🎯 *{total_fetched} Links mil gaye!* (Max 50 per 24 hours)\n\n"
        f"📌 *Note:* Kripya sabhi links ko buzz back karein so everyone benefits!",
        parse_mode="Markdown"
    )

    import asyncio
    for idx, item in enumerate(links, start=1):
        name = escape_md(item["swiggy_name"] or "User")
        url = item["swiggy_link"]
        try:
            await update.message.reply_text(
                f"{idx}\. *{name}*\n🔗 {url}",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        except Exception:
            # Fallback without markdown if name still causes issues
            await update.message.reply_text(
                f"{idx}. {item['swiggy_name'] or 'User'}\n🔗 {url}",
                disable_web_page_preview=True
            )
        # Small delay to avoid hitting Telegram rate limits
        if idx % 10 == 0:
            await asyncio.sleep(0.5)

def get_links_handler():
    return CommandHandler("links", links_command)
