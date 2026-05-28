import os
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from config import IMAGES_DIR
from utils.image_processor import process_images, remove_bg_only
from handlers.payment import send_payment_request
from handlers.start import MAIN_MENU, show_main_menu

# Media group uchun buffer: key -> [(update, photo)]
_mg_buffer: dict[str, list] = {}
_mg_scheduled: set[str] = set()


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

    # To'lov cheki
    if state == "waiting_for_receipt":
        from handlers.payment import handle_receipt
        await handle_receipt(update, context)
        return

    # --- FON OLIB TASHLASH ---
    if state == "remove_bg":
        await _do_remove_bg(update, context)
        return

    # --- FON QO'SHISH: fon rasmi kutilmoqda ---
    if state == "bg_editor_waiting_bg":
        photo = update.message.photo[-1]
        db.set_state(user.id, "bg_editor_active", photo.file_id)
        await update.message.reply_text(
            "✅ <b>Fon saqlandi!</b>\n\n"
            "2️⃣ Endi orqa fonini almashtirmoqchi bo'lgan rasmingizni yuboring.\n"
            "Bir vaqtda bir nechta rasm ham yuborishingiz mumkin 📸",
            parse_mode="HTML"
        )
        return

    # --- FON QO'SHISH: odamning rasmlari ---
    if state == "bg_editor_active":
        photo = update.message.photo[-1]
        mg_id = update.message.media_group_id

        if mg_id:
            # Media group — barchasi kelguncha kutib, keyin barchani qayta ishlash
            key = f"{user.id}_{mg_id}"
            if key not in _mg_buffer:
                _mg_buffer[key] = []
            _mg_buffer[key].append((update, photo))

            if key not in _mg_scheduled:
                _mg_scheduled.add(key)
                asyncio.get_event_loop().create_task(
                    _process_mg_after_delay(key, context, saved_file_id)
                )
        else:
            await _do_bg_editor(update, context, photo, saved_file_id)
        return

    await show_main_menu(update)


async def _process_mg_after_delay(key: str, context, saved_file_id: str, delay: float = 1.5):
    """Media group to'liq kelguncha kutadi, keyin barchani qayta ishlaydi."""
    await asyncio.sleep(delay)
    items = _mg_buffer.pop(key, [])
    _mg_scheduled.discard(key)

    tasks = [
        _do_bg_editor(upd, context, photo, saved_file_id)
        for upd, photo in items
    ]
    await asyncio.gather(*tasks)


async def _do_remove_bg(update: Update, context):
    user = update.effective_user
    photo = update.message.photo[-1]
    processing_msg = await update.message.reply_text("⚡ <b>Ishlanmoqda...</b>", parse_mode="HTML")

    uid = photo.file_id[:10]
    input_path = os.path.join(IMAGES_DIR, f"{user.id}_{uid}_input.jpg")
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
            filename="fonchi_result.png",
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


async def _do_bg_editor(update: Update, context, photo, saved_file_id: str):
    user = update.effective_user
    processing_msg = await update.message.reply_text("⚡ <b>Ishlanmoqda...</b>", parse_mode="HTML")

    uid = photo.file_id[:10]
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
