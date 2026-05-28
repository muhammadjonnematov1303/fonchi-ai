from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.full_name)
    db.clear_state(user.id)

    text = (
        "🤖 <b>Assalomu alaykum!</b>\n\n"
        "⚡ <b>Fonchi AI</b> botiga xush kelibsiz!\n\n"
        "📸 Bu bot yordamida rasmingizning fonini o'zgartirishingiz mumkin.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "🎯 <b>Qanday ishlaydi?</b>\n"
        "1️⃣ Odamning rasmini yuboring\n"
        "2️⃣ Orqa fon rasmini yuboring\n"
        "3️⃣ AI fon almashtiradi ✨\n"
        "━━━━━━━━━━━━━━━\n\n"
        "📲 Boshlash uchun odamning rasmini yuboring!"
    )

    keyboard = [[InlineKeyboardButton("ℹ️ Yordam", callback_data="help"),
                 InlineKeyboardButton("💰 Tarif", callback_data="tarif")]]
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def btn_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "ℹ️ <b>Yordam</b>\n\n"
        "📸 <b>Foydalanish:</b>\n"
        "• Odamning rasmini yuboring\n"
        "• So'ng fon rasmini yuboring\n"
        "• Bot avtomatik fon almashtiradi\n\n"
        "💳 <b>To'lov:</b>\n"
        "• Birinchi marta bepul\n"
        "• Keyingi: 10 000 so'm / 2 kun\n\n"
        "📩 Muammo bo'lsa: @MuhammadjonXP"
    )
    await query.edit_message_text(text, parse_mode="HTML")


async def btn_tarif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "💰 <b>Tariflar</b>\n\n"
        "🆓 Birinchi foydalanish — <b>BEPUL</b>\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💎 <b>Tarif:</b>\n"
        "• 10 000 so'm — <b>2 kun</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "📩 Admin: @MuhammadjonXP"
    )
    await query.edit_message_text(text, parse_mode="HTML")
