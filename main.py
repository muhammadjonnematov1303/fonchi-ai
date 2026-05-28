import sys
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters,
)

import database as db
from config import BOT_TOKEN
from handlers.start import cmd_start, handle_contact
from handlers.image_handler import handle_buttons, handle_photo
from handlers.payment import admin_approve, admin_reject
from handlers.admin import (
    cmd_admin, cmd_grant, cmd_block, cmd_unblock,
    cmd_stats, cmd_users, cmd_addbal, cb_admin
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO, stream=sys.stdout,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logger = logging.getLogger("fonchi")
logger.setLevel(logging.INFO)


async def handle_all_text(update: Update, context):
    text = update.message.text
    from config import COST_PER_IMAGE
    from handlers.image_handler import handle_buttons

    if text == "💰 Balansim":
        user = update.effective_user
        balance = db.get_balance(user.id)
        free = not db.get_user(user.id)["first_free_used"]
        if free:
            status = "🆓 Sizda <b>1 ta bepul</b> foydalanish bor!"
        elif balance >= COST_PER_IMAGE:
            count = balance // COST_PER_IMAGE
            status = f"✅ Balansingizda <b>{count} ta rasm</b> ishlash mumkin."
        else:
            status = "⚠️ Balans yetarli emas. To'lov qiling."
        await update.message.reply_text(
            f"💰 <b>Balansingiz: {balance:,} so'm</b>\n\n"
            f"{status}\n\n"
            f"🖼 1 rasm narxi: <b>{COST_PER_IMAGE:,} so'm</b>",
            parse_mode="HTML"
        )
    elif text in ("🗑 Fon olib tashlash", "🎨 Fon qo'shish"):
        await handle_buttons(update, context)
    else:
        from handlers.start import show_main_menu
        await show_main_menu(update)


async def handle_all_callbacks(update: Update, context):
    data = update.callback_query.data
    if data.startswith("adm_"):
        await cb_admin(update, context)
    elif data.startswith("approve_"):
        await admin_approve(update, context)
    elif data.startswith("reject_"):
        await admin_reject(update, context)


def main():
    db.init_db()

    try:
        logger.info("AI modeli yuklanmoqda...")
        from utils.image_processor import preload_model
        preload_model()
        logger.info("Model tayyor!")
    except Exception as e:
        logger.warning(f"Model yuklanmadi, birinchi so'rovda yuklanadi: {e}")

    from config import PROXY_URL
    builder = Application.builder().token(BOT_TOKEN).concurrent_updates(True)
    if PROXY_URL:
        builder = builder.proxy(PROXY_URL).get_updates_proxy(PROXY_URL)
    app = builder.build()

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("admin",   cmd_admin))
    app.add_handler(CommandHandler("addbal",  cmd_addbal))
    app.add_handler(CommandHandler("grant",   cmd_grant))
    app.add_handler(CommandHandler("block",   cmd_block))
    app.add_handler(CommandHandler("unblock", cmd_unblock))
    app.add_handler(CommandHandler("stats",   cmd_stats))
    app.add_handler(CommandHandler("users",   cmd_users))

    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Barcha callback'larni bitta handler orqali
    app.add_handler(CallbackQueryHandler(handle_all_callbacks))

    logger.info("@FonchiAI_bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()