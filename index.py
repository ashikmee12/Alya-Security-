import asyncio
import re
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from config import BOT_TOKEN, ADMIN_ID, ALLOWED_DOMAINS, ALLOWED_CHANNEL
import database as db

app = Flask(__name__)

# --- COMMAND HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type == "private":
        kb = [
            [InlineKeyboardButton("📢 Official Channel", url="https://t.me/animethic2")],
            [InlineKeyboardButton("🌐 Official Website", url="https://www.animethic.xyz")]
        ]
        if user.id == ADMIN_ID:
            kb.append([InlineKeyboardButton("⚙️ Control Panel", callback_data="admin_panel")])

        await update.message.reply_text(
            f"🛡️ **Animethic Security Guard v2.0**\n\n"
            f"Hello {user.first_name}!\n"
            f"I am the automated group security system for **Animethic**. "
            f"My job is to protect the group from unauthorized links, spam, and forwarded posts.",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("🛡️ Animethic Security Guard is Active and Online!")

# --- IN-BOT SUPER ADMIN PANEL ---
async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("🚫 Access Denied! You are not authorized.", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == "toggle_link":
        db.set_config("antilink", "off" if db.get_config("antilink") == "on" else "on")
    elif data == "toggle_fwd":
        db.set_config("antifwd", "off" if db.get_config("antifwd") == "on" else "on")

    if data in ["admin_panel", "toggle_link", "toggle_fwd"]:
        link_stat = db.get_config("antilink")
        fwd_stat = db.get_config("antifwd")

        kb = [
            [InlineKeyboardButton(f"🔗 Anti-Link Filter: {'✅ ENABLED' if link_stat=='on' else '❌ DISABLED'}", callback_data="toggle_link")],
            [InlineKeyboardButton(f"🔄 Anti-Forward Guard: {'✅ ENABLED' if fwd_stat=='on' else '❌ DISABLED'}", callback_data="toggle_fwd")],
            [InlineKeyboardButton("📊 System & DB Status", callback_data="sys_status")]
        ]
        await query.edit_message_text(
            "⚙️ **Super Admin Control Panel**\n\n"
            "Use the buttons below to toggle security modules in real-time:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )
    elif data == "sys_status":
        kb = [[InlineKeyboardButton("🔙 Back to Panel", callback_data="admin_panel")]]
        await query.edit_message_text(
            "📊 **System Diagnostics:**\n\n"
            "• **Security Guard:** Online 🟢\n"
            "• **Database Engine:** Upstash Redis Connected ⚡\n"
            "• **Hosting Network:** Vercel Serverless Infrastructure 🚀\n"
            "• **Whitelisted Domains:** animethic.xyz, animethic.in\n"
            "• **Whitelisted Channel:** @animethic2",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

# --- SECURITY ENGINE & DETAILED WARNINGS ---
async def handle_security(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.chat.type == "private":
        return

    user_id = msg.from_user.id

    # 1. Anti-Forward Protection
    if db.get_config("antifwd") == "on":
        if msg.forward_date or msg.forward_from or msg.forward_from_chat:
            await msg.delete()
            await apply_warning(
                msg, context, user_id,
                reason="Forwarded message or media detected.",
                rule="Forwarding content from external channels or groups is strictly prohibited."
            )
            return

    # 2. Anti-Link & Username Protection
    if db.get_config("antilink") == "on" and msg.text:
        urls = re.findall(r'(https?://[^\s]+|t\.me/[^\s]+|@[a-zA-Z0-9_]+)', msg.text.lower())
        if urls:
            allowed = False
            for u in urls:
                if any(dom in u for dom in ALLOWED_DOMAINS) or ALLOWED_CHANNEL.lower() in u:
                    allowed = True
                    break
            if not allowed:
                await msg.delete()
                await apply_warning(
                    msg, context, user_id,
                    reason="Unauthorized link or username handle detected.",
                    rule="Only links from animethic.xyz, animethic.in, and @animethic2 are permitted."
                )
                return

async def apply_warning(msg, context, user_id: int, reason: str, rule: str):
    warns = db.add_warn(user_id)
    user_mention = msg.from_user.mention_html()

    if warns >= 3:
        try:
            await context.bot.restrict_chat_member(
                msg.chat_id,
                user_id,
                permissions={"can_send_messages": False}
            )
            mute_text = (
                f"🚫 <b>USER MUTED AUTOMATICALLY</b>\n\n"
                f"👤 <b>User:</b> {user_mention}\n"
                f"⚠️ <b>Reason:</b> Accumulated 3/3 Security Warnings.\n"
                f"🔒 <b>Action:</b> Chat permissions revoked indefinitely."
            )
            await msg.chat.send_message(mute_text, parse_mode="HTML")
            db.reset_warns(user_id)
        except Exception:
            pass
    else:
        remaining = 3 - warns
        kb = [[InlineKeyboardButton("📜 Rules & Channel", url="https://t.me/animethic2")]]
        
        warn_text = (
            f"⚠️ <b>SECURITY WARNING NOTICE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> {user_mention}\n"
            f"🚨 <b>Warning Count:</b> <code>{warns}/3</code>\n\n"
            f"📌 <b>Reason:</b> {reason}\n"
            f"📖 <b>Violated Rule:</b> {rule}\n\n"
            f"❗ <i>Notice: {remaining} more warning(s) will result in an automatic chat mute!</i>"
        )
        await msg.chat.send_message(
            warn_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(kb)
        )

# --- ASYNC PROCESSOR FOR VERCEL ---
async def process_telegram_update(update_json):
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(admin_panel_callback))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_security))

    await application.initialize()
    update = Update.de_json(update_json, application.bot)
    await application.process_update(update)

@app.route("/", methods=["POST"])
def webhook():
    if request.method == "POST":
        update_json = request.get_json(force=True)
        asyncio.run(process_telegram_update(update_json))
        return "OK", 200
    return "Animethic Security Bot Active & Online", 200

if __name__ == "__main__":
    app.run()
