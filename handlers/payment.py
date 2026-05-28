from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
from config import PAYMENT_CARD, PAYMENT_NAME, ADMIN_ID, ADMIN_GROUP_ID


async def send_payment_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        "⚠️ <b>Botdan foydalanish muddati tugagan</b>\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💎 <b>Tarif:</b> 10 000 so'm / 2 kun\n"
        "━━━━━━━━━━━━━━━\n\n"
        "💳 <b>Karta raqami:</b>\n"
        f"<code>{PAYMENT_CARD}</code>\n\n"
        f"👤 <b>Karta egasi:</b> {PAYMENT_NAME}\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📩 To'lov qilgandan keyin <b>chek rasmini</b> yuboring.\n\n"
        "❓ Savollar bo'lsa: @MuhammadjonXP"
    )
    db.set_state(user.id, "waiting_for_receipt")
    await update.message.reply_text(text, parse_mode="HTML")


async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state, _ = db.get_state(user.id)

    if state != "waiting_for_receipt":
        return False

    if not update.message.photo:
        await update.message.reply_text(
            "📸 Iltimos <b>chek rasmini</b> yuboring (rasm ko'rinishida).",
            parse_mode="HTML"
        )
        return True

    photo = update.message.photo[-1]
    payment_id = db.create_payment(user.id, photo.file_id)
    db.clear_state(user.id)

    await update.message.reply_text(
        "⏳ <b>Chekingiz qabul qilindi!</b>\n\n"
        "Admin tekshirib, tez orada tasdiqlaydi.\n"
        "Tasdiqlangach xabar olasiz ✅",
        parse_mode="HTML"
    )

    # Adminga yuborish
    target = ADMIN_GROUP_ID if ADMIN_GROUP_ID else ADMIN_ID
    admin_text = (
        f"💳 <b>Yangi to'lov cheki</b>\n\n"
        f"👤 Foydalanuvchi: <a href='tg://user?id={user.id}'>{user.full_name}</a>\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"🔖 Username: @{user.username or 'yo`q'}\n"
        f"📋 To'lov ID: <code>{payment_id}</code>"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{payment_id}_{user.id}"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data=f"reject_{payment_id}_{user.id}")
        ]
    ]
    try:
        await context.bot.send_photo(
            chat_id=target,
            photo=photo.file_id,
            caption=admin_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text + "\n\n⚠️ Guruhga yuborishda xato.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return True


async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Tasdiqlandi")

    parts = query.data.split("_")
    payment_id = int(parts[1])
    target_user_id = int(parts[2])

    db.update_payment(payment_id, "approved")
    db.grant_subscription(target_user_id, days=2)

    await query.edit_message_caption(
        caption=query.message.caption + "\n\n✅ <b>TASDIQLANDI</b>",
        parse_mode="HTML"
    )

    from handlers.start import MAIN_MENU
    await context.bot.send_message(
        chat_id=target_user_id,
        text=(
            "✅ <b>To'lov tasdiqlandi!</b>\n\n"
            "🎉 Botdan <b>2 kun</b> davomida foydalanishingiz mumkin.\n\n"
            "Quyidagi xizmatlardan birini tanlang 👇"
        ),
        parse_mode="HTML",
        reply_markup=MAIN_MENU
    )


async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("❌ Bekor qilindi")

    parts = query.data.split("_")
    payment_id = int(parts[1])
    target_user_id = int(parts[2])

    db.update_payment(payment_id, "rejected")

    await query.edit_message_caption(
        caption=query.message.caption + "\n\n❌ <b>BEKOR QILINDI</b>",
        parse_mode="HTML"
    )

    await context.bot.send_message(
        chat_id=target_user_id,
        text=(
            "❌ <b>To'lov tasdiqlanmadi.</b>\n\n"
            "Iltimos to'g'ri chek yuborib, qayta urinib ko'ring."
        ),
        parse_mode="HTML"
    )
