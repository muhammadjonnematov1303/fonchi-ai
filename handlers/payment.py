from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
from config import PAYMENT_CARD, PAYMENT_NAME, ADMIN_ID, ADMIN_GROUP_ID, TOPUP_AMOUNT, COST_PER_IMAGE


async def send_payment_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    balance = db.get_balance(user.id)
    text = (
        "⚠️ <b>Balansingiz yetarli emas</b>\n\n"
        f"💳 Joriy balans: <b>{balance:,} so'm</b>\n"
        f"🖼 1 rasm narxi: <b>{COST_PER_IMAGE:,} so'm</b>\n\n"
        "━━━━━━━━━━━━━━━\n"
        f"💎 To'lov miqdori: <b>{TOPUP_AMOUNT:,} so'm</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "💳 <b>Karta raqami:</b>\n"
        f"<code>{PAYMENT_CARD}</code>\n\n"
        f"👤 <b>Karta egasi:</b> {PAYMENT_NAME}\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📩 To'lov qilgandan keyin <b>chek rasmini</b> yuboring.\n\n"
        "❓ Savollar: @MuhammadjonXP"
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
        "Tasdiqlangach balansingiz to'ldiriladi ✅",
        parse_mode="HTML"
    )

    target = ADMIN_GROUP_ID if ADMIN_GROUP_ID else ADMIN_ID
    balance = db.get_balance(user.id)
    admin_text = (
        f"💳 <b>Yangi to'lov cheki</b>\n\n"
        f"👤 Foydalanuvchi: <a href='tg://user?id={user.id}'>{user.full_name}</a>\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"🔖 Username: @{user.username or 'yoq'}\n"
        f"💰 Joriy balans: <b>{balance:,} so'm</b>\n"
        f"➕ Tasdiqlansa qo'shiladi: <b>{TOPUP_AMOUNT:,} so'm</b>\n"
        f"📋 To'lov ID: <code>{payment_id}</code>"
    )
    keyboard = [[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{payment_id}_{user.id}"),
        InlineKeyboardButton("❌ Rad etish",  callback_data=f"reject_{payment_id}_{user.id}")
    ]]
    try:
        await context.bot.send_photo(
            chat_id=target, photo=photo.file_id,
            caption=admin_text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await context.bot.send_message(
            chat_id=ADMIN_ID, text=admin_text + "\n\n⚠️ Guruhga yuborishda xato.",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return True


async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Tasdiqlandi")

    parts = query.data.split("_")
    payment_id = int(parts[1])
    target_user_id = int(parts[2])

    db.update_payment(payment_id, "approved")
    db.add_balance(target_user_id, TOPUP_AMOUNT)
    new_bal = db.get_balance(target_user_id)

    try:
        await query.edit_message_caption(
            caption=query.message.caption + "\n\n✅ <b>TASDIQLANDI</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    from handlers.start import MAIN_MENU
    await context.bot.send_message(
        chat_id=target_user_id,
        text=(
            "✅ <b>To'lov tasdiqlandi!</b>\n\n"
            f"💰 Balansingizga <b>{TOPUP_AMOUNT:,} so'm</b> qo'shildi.\n"
            f"💳 Joriy balans: <b>{new_bal:,} so'm</b>\n\n"
            "Xizmatlardan birini tanlang 👇"
        ),
        parse_mode="HTML",
        reply_markup=MAIN_MENU
    )


async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("❌ Rad etildi")

    parts = query.data.split("_")
    payment_id = int(parts[1])
    target_user_id = int(parts[2])

    db.update_payment(payment_id, "rejected")

    try:
        await query.edit_message_caption(
            caption=query.message.caption + "\n\n❌ <b>RAD ETILDI</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=target_user_id,
        text=(
            "❌ <b>To'lov tasdiqlanmadi.</b>\n\n"
            "Iltimos to'g'ri chek yuborib, qayta urinib ko'ring."
        ),
        parse_mode="HTML"
    )