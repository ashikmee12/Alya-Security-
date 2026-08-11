import os
import asyncio
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token নেওয়ার সময় অটোমেটিক .strip() করা
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

# Flask App Initialisation
app = Flask(__name__)

# Application Builder
telegram_app = Application.builder().token(BOT_TOKEN).build()


# --- Control Panel Keyboard ---
def build_control_panel():
    antifwd = db.get_config("antifwd", "off")
    antilink = db.get_config("antilink", "off")

    btn_fwd = f"Anti-Forward: {'✅ ON' if antifwd == 'on' else '❌ OFF'}"
    btn_link = f"Anti-Link: {'✅ ON' if antilink == 'on' else '❌ OFF'}"

    keyboard = [
        [InlineKeyboardButton(btn_fwd, callback_data="toggle_antifwd")],
        [InlineKeyboardButton(btn_link, callback_data="toggle_antilink")],
        [InlineKeyboardButton("🔄 Refresh Panel", callback_data="refresh_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Command & Event Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text(
            "👋 Hello! Add me to your group as an Admin to enable security protections."
        )
    else:
        await update.message.reply_text(
            "⚙️ **Group Security Control Panel**",
            parse_mode="Markdown",
            reply_markup=build_control_panel()
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "toggle_antifwd":
        current = db.get_config("antifwd", "off")
        db.set_config("antifwd", "off" if current == "on" else "on")
    elif data == "toggle_antilink":
        current = db.get_config("antilink", "off")
        db.set_config("antilink", "off" if current == "on" else "on")

    try:
        await query.edit_message_text(
            "⚙️ **Group Security Control Panel**",
            parse_mode="Markdown",
            reply_markup=build_control_panel()
        )
    except Exception as e:
        logger.warning(f"Message edit error: {e}")


async def handle_security(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or (message.from_user and message.from_user.is_bot):
        return

    chat = update.effective_chat
    if chat.type not in ["group", "supergroup"]:
        return

    # 1. Anti-Forward Check
    if db.get_config("antifwd") == "on":
        if message.forward_date or message.forward_from or message.forward_from_chat:
            try:
                await message.delete()
                return
            except Exception as e:
                logger.error(f"Anti-Forward deletion failed: {e}")

    # 2. Anti-Link Check
    if db.get_config("antilink") == "on":
        text = message.text or message.caption or ""
        if "http://" in text or "https://" in text or "t.me/" in text or "telegram.me/" in text:
            try:
                await message.delete()
                return
            except Exception as e:
                logger.error(f"Anti-Link deletion failed: {e}")


# --- Register Handlers ---
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("settings", start_command))
telegram_app.add_handler(CallbackQueryHandler(button_handler))
telegram_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_security))


# --- Async Processing function for Vercel ---
async def process_telegram_update(update_json):
    async with telegram_app:
        update = Update.de_json(update_json, telegram_app.bot)
        await telegram_app.process_update(update)


# --- Flask Webhook Route ---
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "Alya Security Bot is running!", 200

    if request.method == 'POST':
        try:
            update_json = request.get_json(force=True)
            asyncio.run(process_telegram_update(update_json))
            return "OK", 200
        except Exception as e:
            logger.error(f"Error handling webhook request: {e}")
            return "Internal Server Error", 500


if __name__ == '__main__':
    app.run()
