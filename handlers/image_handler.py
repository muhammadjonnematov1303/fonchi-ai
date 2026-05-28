import os
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from config import IMAGES_DIR
from utils.image_processor import process_images, remove_bg_only
from handlers.payment import send_payment_request
from handlers.start import MAIN_MENU, show_main_menu


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if db.is_blocked(user.id):
        await update.message.reply_text("🚫 Siz bloklangansiz.")
        return

    if not db.is_registered(user.id):
        await update.message.reply_text("Iltimos /start bosing va ro'yxatdan o'ting.")
        return

    if text == "🗑 Fon olib tashlash":
        if not db.has_access(user.id, user.username or ""):
            await send_payment_request(update, context)
            return
        db.set_state(user.id, "remove_bg")
        await update.message.reply_text(
            "🗑 <b>Fon olib tashlash</b>\n\n"
            "📸 Rasmni yuboring — fon olinib, PNG fayl sifatida qaytariladi.",
            parse_mode="HTML"
        )

    elif text == "🎨 Fon qo'shish":
        if not db.has_access(user.id, user.username or ""):
            await send_payment_request(update, context)
            return
        db.set_state(user.id, "bg_editor_waiting_bg")
        await update.message.reply_text(
            "🎨 <b>Fon qo'shish</b>\n\n"
            "1️⃣ Avval <b>orqa fon rasmini</b> yuboring.",
            parse_mode="HTML"
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if db.is_blocked(user.id):
        await update.message.reply_text("🚫 Siz bloklangansiz.")
        return

    if not db.is_registered(user.id):
        await update.message.reply_text("Iltimos /start bosing va ro'yxatdan o'ting.")
        return

    state, saved_file_id = db.get_state(user.id)

    # To'lov cheki kutilmoqda
    if state == "waiting_for_receipt":
        from handlers.payment import handle_receipt
        await handle_receipt(update, context)
        return

    # --- FON OLIB TASHLASH ---
    if state == "remove_bg":
        photo = update.message.photo[-1]
        processing_msg = await update.message.reply_text("⚡ <b>Ishlanmoqda...</b>", parse_mode="HTML")

        input_path = os.path.join(IMAGES_DIR, f"{user.id}_input.jpg")
        try:
            file = await context.bot.get_file(photo.file_id)
            await file.download_to_drive(input_path)

            loop = asyncio.get_event_loop()
            png_bytes = await loop.run_in_executor(None, remove_bg_only, input_path)

            db.mark_free_used(user.id)
            db.clear_state(user.id)
            await processing_msg.delete()

            await update.message.reply_document(
                document=png_bytes,
                filename="result.png",
                caption="✅ <b>Tayyor!</b> Fon olib tashlandi.",
                parse_mode="HTML",
                reply_markup=MAIN_MENU
            )
        except Exception:
            db.clear_state(user.id)
            await processing_msg.edit_text("❌ Xato yuz berdi. Qayta urinib ko'ring.")
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
        return

    # --- FON QO'SHISH: fon rasmi kutilmoqda ---
    if state == "bg_editor_waiting_bg":
        photo = update.message.photo[-1]
        db.set_state(user.id, "bg_editor_active", photo.file_id)
        await update.message.reply_text(
            "✅ <b>Fon saqlandi!</b>\n\n"
            "2️⃣ Endi odamning rasmini yuboring.\n"
            "Bir vaqtda bir nechta rasm ham yuborishingiz mumkin 📸",
            parse_mode="HTML"
        )
        return

    # --- FON QO'SHISH: odamning rasm(lar)i ---
    if state == "bg_editor_active":
        photo = update.message.photo[-1]
        uid = photo.file_id[:10]
        processing_msg = await update.message.reply_text("⚡ <b>Ishlanmoqda...</b>", parse_mode="HTML")

        person_path = os.path.join(IMAGES_DIR, f"{user.id}_{uid}_person.jpg")
        bg_path     = os.path.join(IMAGES_DIR, f"{user.id}_{uid}_bg.jpg")
        output_path = os.path.join(IMAGES_DIR, f"{user.id}_{uid}_result.jpg")

        try:
            person_file = await context.bot.get_file(photo.file_id)
            bg_file     = await context.bot.get_file(saved_file_id)
            await person_file.download_to_drive(person_path)
            await bg_file.download_to_drive(bg_path)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, process_images, person_path, bg_path, output_path)

            db.mark_free_used(user.id)
            await processing_msg.delete()

            with open(output_path, "rb") as f:
                await update.message.reply_photo(
                    photo=f,
                    caption="✅ <b>Tayyor!</b> Yana rasm yuborishingiz mumkin.",
                    parse_mode="HTML"
                )
        except Exception:
            await processing_msg.edit_text("❌ Xato yuz berdi. Qayta urinib ko'ring.")
        finally:
            for path in [person_path, bg_path, output_path]:
                if os.path.exists(path):
                    os.remove(path)
        return

    # Hech qanday holat yo'q — menyu ko'rsat
    await show_main_menu(update)
