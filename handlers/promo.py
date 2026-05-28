from telegram import Update
from telegram.ext import ContextTypes
import database as db
from handlers.start import MAIN_MENU


async def handle_promo_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.set_state(user.id, "waiting_for_promo")
    await update.message.reply_text(
        "🎁 <b>Promokod kiriting:</b>\n\n"
        "Promokodingizni yuboring — balansingizga qo'shiladi.",
        parse_mode="HTML"
    )


async def handle_promo_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    code = update.message.text.strip()

    success, msg, amount = db.use_promo(user.id, code)
    db.clear_state(user.id)

    if success:
        balance = db.get_balance(user.id)
        await update.message.reply_text(
            f"{msg}\n\n"
            f"➕ Qo'shildi: <b>{amount:,} so'm</b>\n"
            f"💰 Joriy balans: <b>{balance:,} so'm</b>",
            parse_mode="HTML",
            reply_markup=MAIN_MENU
        )
    else:
        await update.message.reply_text(msg, reply_markup=MAIN_MENU)
