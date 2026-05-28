from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
from config import COST_PER_IMAGE


MAIN_MENU = ReplyKeyboardMarkup(
    [["🗑 Fon olib tashlash", "🎨 Fon qo'shish"],
     ["💰 Balansim", "🎁 Promokod"]],
    resize_keyboard=True
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.full_name)
    db.clear_state(user.id)

    if db.is_registered(user.id):
        balance = db.get_balance(user.id)
        free = not db.get_user(user.id)["first_free_used"]
        bal_text = "🆓 Birinchi foydalanish bepul!" if free else f"💰 Balansingiz: <b>{balance:,} so'm</b>"
        await update.message.reply_text(
            f"👋 Xush kelibsiz!\n\n{bal_text}\n\nXizmat tanlang 👇",
            parse_mode="HTML",
            reply_markup=MAIN_MENU
        )
        return

    db.set_state(user.id, "waiting_for_phone")
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
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
        "🆓 Birinchi foydalanish <b>bepul</b>!\n\n"
        "Xizmat tanlang 👇",
        parse_mode="HTML",
        reply_markup=MAIN_MENU
    )


async def show_main_menu(update: Update):
    user = update.effective_user
    balance = db.get_balance(user.id)
    free = not db.get_user(user.id)["first_free_used"]
    bal_text = "🆓 Birinchi foydalanish bepul!" if free else f"💰 Balans: <b>{balance:,} so'm</b>"
    await update.message.reply_text(
        f"{bal_text}\n\nXizmat tanlang 👇",
        parse_mode="HTML",
        reply_markup=MAIN_MENU
    )