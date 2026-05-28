import os
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from config import IMAGES_DIR
from utils.image_processor import process_images
from handlers.payment import send_payment_request


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if db.is_blocked(user.id):
        await update.message.reply_text("🚫 Siz bloklangansiz. Admin bilan bog'laning.")
        return

    state, photo_file_id = db.get_state(user.id)

    # Chek kutilayotgan bo'lsa
    if state == "waiting_for_receipt":
        from handlers.payment import handle_receipt
        await handle_receipt(update, context)
        return

    # Birinchi rasm — odamning rasmi
    if state is None or state == "":
        if not db.has_access(user.id, user.username or ""):
            await send_payment_request(update, context)
            return

        photo = update.message.photo[-1]
        db.set_state(user.id, "waiting_for_bg", photo.file_id)

        await update.message.reply_text(
            "✅ <b>Rasm qabul qilindi!</b>\n\n"
            "🖼 Endi <b>orqa fon rasmini</b> yuboring.\n"
            "(Fon sifatida ishlatiladigan rasm)",
            parse_mode="HTML"
        )
        return

    # Ikkinchi rasm — fon rasmi
    if state == "waiting_for_bg":
        bg_photo = update.message.photo[-1]

        processing_msg = await update.message.reply_text(
            "⚡ <b>AI ishlamoqda...</b>\n\n"
            "⏳ Fon almashtirilmoqda, biroz kuting...",
            parse_mode="HTML"
        )

        person_path = os.path.join(IMAGES_DIR, f"{user.id}_person.jpg")
        bg_path = os.path.join(IMAGES_DIR, f"{user.id}_bg.jpg")
        output_path = os.path.join(IMAGES_DIR, f"{user.id}_result.jpg")

        try:
            # Rasmlarni yuklab olish
            person_file = await context.bot.get_file(photo_file_id)
            bg_file = await context.bot.get_file(bg_photo.file_id)

            await person_file.download_to_drive(person_path)
            await bg_file.download_to_drive(bg_path)

            # AI orqali qayta ishlash (thread poolda)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, process_images, person_path, bg_path, output_path
            )

            db.mark_free_used(user.id)
            db.clear_state(user.id)

            await processing_msg.delete()

            with open(output_path, "rb") as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=(
                        "✅ <b>Tayyor!</b>\n\n"
                        "🎨 Fon muvaffaqiyatli almashtirildi!\n"
                        "📸 Yana rasm yuborish uchun rasmingizni yuboring."
                    ),
                    parse_mode="HTML"
                )

        except Exception as e:
            db.clear_state(user.id)
            await processing_msg.edit_text(
                "❌ <b>Xato yuz berdi.</b>\n\n"
                "Iltimos qayta urinib ko'ring yoki boshqa rasm yuboring.",
                parse_mode="HTML"
            )
        finally:
            for path in [person_path, bg_path, output_path]:
                if os.path.exists(path):
                    os.remove(path)
