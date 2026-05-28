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
from handlers.start import cmd_start, handle_contact
from handlers.image_handler import handle_buttons, handle_photo
from handlers.payment import admin_approve, admin_reject
from handlers.admin import cmd_admin, cmd_grant, cmd_block, cmd_unblock, cmd_stats, cmd_users, cb_admin

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


def main():
    db.init_db()

    try:
        logger.info("AI modeli yuklanmoqda...")
        from utils.image_processor import preload_model
        preload_model()
        logger.info("Model tayyor!")
    except Exception as e:
        logger.warning(f"Model yuklanmadi, birinchi so'rovda yuklanadi: {e}")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    # Asosiy komandalar
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("grant", cmd_grant))
    app.add_handler(CommandHandler("block", cmd_block))
    app.add_handler(CommandHandler("unblock", cmd_unblock))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("users", cmd_users))

    # Telefon raqam
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))

    # Menyu tugmalari
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^(🗑 Fon olib tashlash|🎨 Fon qo'shish)$"),
        handle_buttons
    ))

    # Rasmlar
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Admin panel tugmalari
    app.add_handler(CallbackQueryHandler(cb_admin, pattern=r"^admin_(users|stats|grant|block|back)$"))

    # To'lov tasdiqlash tugmalari
    app.add_handler(CallbackQueryHandler(admin_approve, pattern=r"^approve_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_reject, pattern=r"^reject_\d+_\d+$"))

    logger.info("@FonchiAI_bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
