from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import database as db


MAIN_MENU = ReplyKeyboardMarkup(
    [["🗑 Fon olib tashlash", "🎨 Fon qo'shish"]],
    resize_keyboard=True
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.full_name)
    db.clear_state(user.id)

    if db.is_registered(user.id):
        await update.message.reply_text(
            "👋 Xush kelibsiz!\n\nQuyidagi xizmatlardan birini tanlang:",
            reply_markup=MAIN_MENU
        )
        return

    db.set_state(user.id, "waiting_for_phone")
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text(
        "👋 <b>Assalomu alaykum!</b>\n\n"
        "⚡ <b>Fonchi AI</b> botiga xush kelibsiz!\n\n"
        "Botdan foydalanish uchun telefon raqamingizni yuboring 👇",
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact = update.message.contact

    db.save_phone(user.id, contact.phone_number)
    db.clear_state(user.id)

    await update.message.reply_text(
        "✅ <b>Ro'yxatdan o'tdingiz!</b>\n\n"
        "Quyidagi xizmatlardan birini tanlang 👇",
        parse_mode="HTML",
        reply_markup=MAIN_MENU
    )


async def show_main_menu(update: Update):
    await update.message.reply_text(
        "Xizmat tanlang 👇",
        reply_markup=MAIN_MENU
    )
