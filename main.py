import sys
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import database as db
from config import BOT_TOKEN
from handlers.start import cmd_start, btn_help, btn_tarif
from handlers.image_handler import handle_photo
from handlers.payment import handle_receipt, admin_approve, admin_reject
from handlers.admin import (
    cmd_admin, cmd_grant, cmd_block, cmd_unblock, cmd_stats, cmd_users
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.WARNING,
    stream=sys.stdout,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logger = logging.getLogger("fonchi")
logger.setLevel(logging.INFO)


async def handle_message(update: Update, context):
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


async def handle_photo_or_receipt(update: Update, context):
    state, _ = db.get_state(update.effective_user.id)
    if state == "waiting_for_receipt":
        await handle_receipt(update, context)
    else:
        await handle_photo(update, context)


def main():
    db.init_db()

    logger.info("AI modeli yuklanmoqda...")
    from utils.image_processor import preload_model
    preload_model()
    logger.info("Model tayyor. Bot ishga tushmoqda...")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("grant", cmd_grant))
    app.add_handler(CommandHandler("block", cmd_block))
    app.add_handler(CommandHandler("unblock", cmd_unblock))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_or_receipt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(btn_help, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(btn_tarif, pattern="^tarif$"))
    app.add_handler(CallbackQueryHandler(admin_approve, pattern=r"^approve_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_reject, pattern=r"^reject_\d+_\d+$"))

    logger.info("@FonchiAI_bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
