import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

ADMIN_CHAT_ID = 492853177

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("ENV VAR TOKEN не знайдено")

BEER_MENU = {
    "IPA": "60 грн/л",
    "Лагер": "50 грн/л",
    "Пшеничне": "55 грн/л",
}

VOLUMES = ["0.5л", "1л", "2л"]
NEW_ITEMS = ["Медовий Ель", "Темне карамельне"]
PROMOTIONS = ["Знижка 10% на IPA", "3л Лагеру = 4-й безкоштовно"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🍺 Меню", callback_data="menu")],
        [InlineKeyboardButton("🆕 Новинки", callback_data="new")],
        [InlineKeyboardButton("🔥 Акції", callback_data="promo")],
        [InlineKeyboardButton("🛒 Замовити", callback_data="order")],
    ]
    await update.message.reply_text(
        "Вітаємо у 🍻 *BeerTime*! Оберіть дію:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        text = "\n".join([f"{b} — {p}" for b, p in BEER_MENU.items()])
        await query.edit_message_text(f"🍺 *Меню:*\n\n{text}", parse_mode="Markdown")

    elif data == "new":
        text = "\n".join([f"• {i}" for i in NEW_ITEMS])
        await query.edit_message_text(f"🆕 *Новинки:*\n\n{text}", parse_mode="Markdown")

    elif data == "promo":
        text = "\n".join([f"• {p}" for p in PROMOTIONS])
        await query.edit_message_text(f"🔥 *Акції:*\n\n{text}", parse_mode="Markdown")

    elif data == "order":
        buttons = [[InlineKeyboardButton(b, callback_data=f"beer_{b}")] for b in BEER_MENU]
        await query.edit_message_text("Оберіть пиво:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("beer_"):
        beer = data.replace("beer_", "")
        context.user_data["beer"] = beer
        buttons = [[InlineKeyboardButton(v, callback_data=f"vol_{v}")] for v in VOLUMES]
        await query.edit_message_text(
            f"Обʼєм для *{beer}*: ",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("vol_"):
        volume = data.replace("vol_", "")
        beer = context.user_data.get("beer", "Невідомо")
        user = query.from_user

        order_text = f"{beer} — {volume}"

        await query.edit_message_text(
            f"✅ Замовлення прийнято!\n\n*{order_text}*\n📍 вул. Пивна, 12",
            parse_mode="Markdown"
        )

        username = f"@{user.username}" if user.username else "(без username)"
        msg_admin = (
            f"📦 *Нове замовлення*\n"
            f"👤 {user.full_name} {username}\n"
            f"🍺 {order_text}"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg_admin, parse_mode="Markdown")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
