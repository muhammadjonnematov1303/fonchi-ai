import os
import sys
import asyncio
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters,
)

from config import BOT_TOKEN
import database as db

logging.basicConfig(level=logging.WARNING)

flask_app = Flask(__name__)
app = flask_app  # Vercel shu nomni qidiradi

db.init_db()

_ptb: Application = None


def build_ptb() -> Application:
    global _ptb
    if _ptb is not None:
        return _ptb

    from handlers.start import cmd_start, btn_help, btn_tarif
    from handlers.image_handler import handle_photo
    from handlers.payment import handle_receipt, admin_approve, admin_reject
    from handlers.admin import (
        cmd_admin, cmd_grant, cmd_block, cmd_unblock, cmd_stats, cmd_users
    )

    async def handle_photo_or_receipt(update, context):
        state, _ = db.get_state(update.effective_user.id)
        if state == "waiting_for_receipt":
            await handle_receipt(update, context)
        else:
            await handle_photo(update, context)

    async def handle_message(update, context):
        user = update.effective_user
        if db.is_blocked(user.id):
            return
        state, _ = db.get_state(user.id)
        if state == "waiting_for_receipt":
            await update.message.reply_text(
                "📸 Iltimos <b>chek rasmini</b> yuboring.", parse_mode="HTML"
            )
            return
        await update.message.reply_text(
            "📸 Boshlash uchun odamning rasmini yuboring.", parse_mode="HTML"
        )

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("admin", cmd_admin))
    application.add_handler(CommandHandler("grant", cmd_grant))
    application.add_handler(CommandHandler("block", cmd_block))
    application.add_handler(CommandHandler("unblock", cmd_unblock))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("users", cmd_users))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_or_receipt))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(btn_help, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(btn_tarif, pattern="^tarif$"))
    application.add_handler(CallbackQueryHandler(admin_approve, pattern=r"^approve_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(admin_reject, pattern=r"^reject_\d+_\d+$"))

    _ptb = application
    return _ptb


@flask_app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "bot": "@FonchiAI_bot"})


@flask_app.route("/api/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    ptb = build_ptb()

    async def process():
        await ptb.initialize()
        update = Update.de_json(data, ptb.bot)
        await ptb.process_update(update)

    asyncio.run(process())
    return jsonify({"ok": True})


@flask_app.route("/api/setup", methods=["GET"])
def setup_webhook():
    """Webhookni Telegram ga ro'yxatdan o'tkazish"""
    import urllib.request
    import urllib.parse

    host = request.host_url.rstrip("/")
    webhook_url = f"{host}/api/webhook"
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    params = urllib.parse.urlencode({"url": webhook_url, "drop_pending_updates": "true"})

    with urllib.request.urlopen(f"{api_url}?{params}") as resp:
        result = resp.read().decode()

    return jsonify({"webhook": webhook_url, "telegram_response": result})
