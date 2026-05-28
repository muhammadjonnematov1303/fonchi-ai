from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
from config import ADMIN_ID
from datetime import datetime, timezone


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    total, active, today_payments = db.get_stats()

    text = (
        "👑 <b>Admin Panel</b>\n\n"
        "━━━━━━━━━━━━━━━\n"
        f"👥 Jami foydalanuvchilar: <b>{total}</b>\n"
        f"✅ Aktiv obunalar: <b>{active}</b>\n"
        f"💰 Bugungi to'lovlar: <b>{today_payments}</b>\n"
        "━━━━━━━━━━━━━━━"
    )

    keyboard = [
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton("➕ Obuna berish", callback_data="admin_grant"),
         InlineKeyboardButton("🚫 Bloklash", callback_data="admin_block")],
    ]
    await update.message.reply_text(
        text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cmd_grant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Ishlatish: /grant <user_id> [kunlar]")
        return
    try:
        target_id = int(args[0])
        days = int(args[1]) if len(args) > 1 else 2
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format.")
        return

    user = db.get_user(target_id)
    if not user:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return

    db.grant_subscription(target_id, days)
    await update.message.reply_text(f"✅ {target_id} ga {days} kunlik obuna berildi.")

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                f"🎉 <b>Admin sizga {days} kunlik obuna berdi!</b>\n\n"
                "📸 Endi botdan foydalanishingiz mumkin."
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass


async def cmd_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Ishlatish: /block <user_id>")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format.")
        return

    db.block_user(target_id)
    await update.message.reply_text(f"🚫 {target_id} bloklandi.")


async def cmd_unblock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Ishlatish: /unblock <user_id>")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format.")
        return

    db.unblock_user(target_id)
    await update.message.reply_text(f"✅ {target_id} blokdan chiqarildi.")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    total, active, today_payments = db.get_stats()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    text = (
        "📊 <b>Statistika</b>\n\n"
        f"🕐 Vaqt: {now}\n\n"
        f"👥 Jami userlar: <b>{total}</b>\n"
        f"✅ Aktiv obunalar: <b>{active}</b>\n"
        f"💰 Bugungi to'lovlar: <b>{today_payments}</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    users = db.get_all_users()
    if not users:
        await update.message.reply_text("Hali foydalanuvchilar yo'q.")
        return

    lines = ["👥 <b>Foydalanuvchilar ro'yxati:</b>\n"]
    for u in users[:20]:
        status = "✅" if u["subscription_until"] else ("🆓" if not u["first_free_used"] else "⛔")
        lines.append(
            f"{status} <code>{u['user_id']}</code> — {u['full_name'] or 'Noma\'lum'}"
        )

    if len(users) > 20:
        lines.append(f"\n... va yana {len(users) - 20} ta")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
