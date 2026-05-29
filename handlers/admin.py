from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
from config import ADMIN_ID, COST_PER_IMAGE
from datetime import datetime, timezone
import logging
import os

logger = logging.getLogger("fonchi")


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def _main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="adm_users")],
        [InlineKeyboardButton("📊 Statistika",       callback_data="adm_stats")],
        [InlineKeyboardButton("💰 Balans to'ldirish", callback_data="adm_balance"),
         InlineKeyboardButton("🚫 Bloklash",          callback_data="adm_block")],
    ])


def _main_text():
    total, with_balance, today = db.get_stats()
    return (
        "👑 <b>Admin Panel</b>\n\n"
        "━━━━━━━━━━━━━━━\n"
        f"👥 Jami foydalanuvchilar: <b>{total}</b>\n"
        f"💰 Balansli userlar: <b>{with_balance}</b>\n"
        f"✅ Bugungi to'lovlar: <b>{today}</b>\n"
        "━━━━━━━━━━━━━━━"
    )


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        _main_text(), parse_mode="HTML", reply_markup=_main_keyboard()
    )


async def cb_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    data = query.data
    back_btn = [[InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")]]

    try:
        if data == "adm_stats":
            total, with_balance, today = db.get_stats()
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            text = (
                "📊 <b>Statistika</b>\n\n"
                f"🕐 Vaqt: {now}\n\n"
                f"👥 Jami userlar: <b>{total}</b>\n"
                f"💰 Balansli userlar: <b>{with_balance}</b>\n"
                f"✅ Bugungi to'lovlar: <b>{today}</b>\n"
                f"🖼 1 rasm narxi: <b>{COST_PER_IMAGE} so'm</b>"
            )
            await query.edit_message_text(text, parse_mode="HTML",
                                          reply_markup=InlineKeyboardMarkup(back_btn))

        elif data == "adm_users":
            users = db.get_all_users()
            if not users:
                await query.edit_message_text("Hali foydalanuvchilar yo'q.",
                                              reply_markup=InlineKeyboardMarkup(back_btn))
                return
            lines = ["👥 <b>Foydalanuvchilar:</b>\n"]
            for u in users[:20]:
                bal = u["balance"] or 0
                blocked = " 🚫" if u["is_blocked"] else ""
                free = " 🆓" if not u["first_free_used"] else ""
                lines.append(
                    f"<code>{u['user_id']}</code> — {u['full_name'] or 'Noma\'lum'}{free}{blocked}\n"
                    f"   💰 {bal:,} so'm"
                )
            if len(users) > 20:
                lines.append(f"\n... va yana {len(users) - 20} ta")
            await query.edit_message_text(
                "\n".join(lines), parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(back_btn)
            )

        elif data == "adm_balance":
            await query.edit_message_text(
                "💰 <b>Balans to'ldirish</b>\n\n"
                "Foydalanuvchiga balans qo'shish uchun:\n"
                "<code>/addbal &lt;user_id&gt; &lt;summa&gt;</code>\n\n"
                "📌 Misol:\n"
                "<code>/addbal 123456789 10000</code>\n\n"
                "Foydalanuvchi ID sini /users buyrug'i orqali toping.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(back_btn)
            )

        elif data == "adm_block":
            await query.edit_message_text(
                "🚫 <b>Bloklash / Blokdan chiqarish</b>\n\n"
                "<code>/block &lt;user_id&gt;</code> — bloklash\n"
                "<code>/unblock &lt;user_id&gt;</code> — blokdan chiqarish",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(back_btn)
            )

        elif data == "adm_back":
            await query.edit_message_text(
                _main_text(), parse_mode="HTML", reply_markup=_main_keyboard()
            )

    except Exception as e:
        logger.error(f"cb_admin error: {e}")


async def cmd_addbal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Ishlatish: /addbal <user_id> <summa>")
        return
    try:
        target_id = int(args[0])
        amount = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format.")
        return

    user = db.get_user(target_id)
    if not user:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return

    db.add_balance(target_id, amount)
    new_bal = db.get_balance(target_id)
    await update.message.reply_text(
        f"✅ <code>{target_id}</code> ga <b>{amount:,} so'm</b> qo'shildi.\n"
        f"💰 Yangi balans: <b>{new_bal:,} so'm</b>",
        parse_mode="HTML"
    )
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"💰 <b>Balansingiz to'ldirildi!</b>\n\n"
                 f"➕ Qo'shildi: <b>{amount:,} so'm</b>\n"
                 f"💳 Joriy balans: <b>{new_bal:,} so'm</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


async def cmd_grant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Ishlatish: /grant <user_id> [summa]")
        return
    try:
        target_id = int(args[0])
        amount = int(args[1]) if len(args) > 1 else 10000
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format.")
        return
    user = db.get_user(target_id)
    if not user:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return
    db.add_balance(target_id, amount)
    await update.message.reply_text(f"✅ {target_id} ga {amount:,} so'm qo'shildi.")


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


async def cmd_addpromo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Ishlatish: /addpromo &lt;KOD&gt; &lt;summa&gt; [necha_marta]\n\n"
            "Misol:\n/addpromo SALE2024 5000 10\n/addpromo VIP 10000"
        )
        return
    try:
        code = args[0].upper()
        amount = int(args[1])
        uses = int(args[2]) if len(args) > 2 else -1
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format.")
        return
    db.create_promo(code, amount, uses)
    uses_text = f"{uses} marta" if uses > 0 else "Cheksiz"
    await update.message.reply_text(
        f"✅ <b>Promokod yaratildi!</b>\n\n"
        f"🔑 Kod: <code>{code}</code>\n"
        f"💰 Summa: <b>{amount:,} so'm</b>\n"
        f"🔄 Foydalanish: <b>{uses_text}</b>",
        parse_mode="HTML"
    )


async def cmd_promos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    promos = db.get_all_promos()
    if not promos:
        await update.message.reply_text("Hali promokodlar yo'q.")
        return
    lines = ["🎁 <b>Promokodlar:</b>\n"]
    for p in promos:
        uses = "∞" if p["uses_left"] == -1 else str(p["uses_left"])
        lines.append(f"<code>{p['code']}</code> — {p['amount']:,} so'm | Qoldi: {uses}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_delpromo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Ishlatish: /delpromo &lt;KOD&gt;")
        return
    code = context.args[0].upper()
    db.delete_promo(code)
    await update.message.reply_text(f"🗑 <code>{code}</code> o'chirildi.", parse_mode="HTML")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    total, with_balance, today = db.get_stats()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    await update.message.reply_text(
        f"📊 <b>Statistika</b>\n\n🕐 {now}\n\n"
        f"👥 Jami: <b>{total}</b>\n"
        f"💰 Balansli: <b>{with_balance}</b>\n"
        f"✅ Bugungi: <b>{today}</b>",
        parse_mode="HTML"
    )


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    users = db.get_all_users()
    if not users:
        await update.message.reply_text("Hali foydalanuvchilar yo'q.")
        return
    lines = ["👥 <b>Foydalanuvchilar:</b>\n"]
    for u in users[:20]:
        bal = u["balance"] or 0
        lines.append(f"<code>{u['user_id']}</code> — {u['full_name'] or 'Noma\'lum'} | 💰{bal:,}")
    if len(users) > 20:
        lines.append(f"\n... va yana {len(users) - 20} ta")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("🛑 <b>Bot to'xtatilmoqda...</b>", parse_mode="HTML")
    os._exit(0)