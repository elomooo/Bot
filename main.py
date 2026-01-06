import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# =====================
# CONFIG
# =====================

ADMIN_CHAT_ID = 492853177  # ← адмін
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN not found")

# =====================
# DATA (editable)
# =====================

BEER_MENU = {
    "IPA": "60 грн/л",
    "Лагер": "50 грн/л",
    "Пшеничне": "55 грн/л",
}

VOLUMES = ["0.5л", "1л", "1.5л", "2л"]

# =====================
# KEYBOARDS
# =====================

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🍺 Меню", callback_data="menu"),
            InlineKeyboardButton("🛒 Кошик", callback_data="cart"),
        ],
        [
            InlineKeyboardButton("🛒 Замовити", callback_data="order"),
        ]
    ])

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Додати товар", callback_data="admin_add")],
        [InlineKeyboardButton("✏ Змінити товар", callback_data="admin_edit")],
        [InlineKeyboardButton("❌ Видалити товар", callback_data="admin_delete")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back")]
    ])

# =====================
# START
# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("cart", [])
    await update.message.reply_text(
        "🍻 *BeerTime*\nОберіть дію:",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# =====================
# BUTTONS
# =====================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id

    # ---------- CLIENT ----------
    if data == "menu":
        text = "\n".join([f"{k} — {v}" for k, v in BEER_MENU.items()])
        await query.edit_message_text(
            f"🍺 *Меню:*\n\n{text}",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    elif data == "order":
        buttons = [
            [InlineKeyboardButton(b, callback_data=f"beer_{b}")]
            for b in BEER_MENU
        ]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="back")])
        await query.edit_message_text(
            "Оберіть пиво:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("beer_"):
        beer = data.replace("beer_", "")
        context.user_data["beer"] = beer
        buttons = [
            [InlineKeyboardButton(v, callback_data=f"vol_{v}")]
            for v in VOLUMES
        ]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="order")])
        await query.edit_message_text(
            f"{beer} — обʼєм:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("vol_"):
        volume = data.replace("vol_", "")
        beer = context.user_data["beer"]
        context.user_data["cart"].append(f"{beer} ({volume})")
        await query.edit_message_text(
            "✅ Додано в кошик",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Додати ще", callback_data="order")],
                [InlineKeyboardButton("🛒 Кошик", callback_data="cart")]
            ])
        )

    elif data == "cart":
        cart = context.user_data.get("cart", [])
        if not cart:
            await query.edit_message_text(
                "🛒 Кошик порожній",
                reply_markup=main_menu()
            )
            return

        text = "\n".join([f"• {i}" for i in cart])
        await query.edit_message_text(
            f"🛒 *Ваш кошик:*\n\n{text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Оформити", callback_data="checkout")],
                [InlineKeyboardButton("⬅ Назад", callback_data="back")]
            ])
        )

    elif data == "checkout":
        context.user_data["await_phone"] = True
        await query.message.reply_text(
            "📞 Надішліть номер телефону",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📞 Надіслати номер", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )

    # ---------- ADMIN ----------
    elif data == "admin" and uid == ADMIN_CHAT_ID:
        await query.edit_message_text(
            "⚙ Адмін панель",
            reply_markup=admin_menu()
        )

    elif data == "admin_add" and uid == ADMIN_CHAT_ID:
        context.user_data["admin_action"] = "add"
        await query.message.reply_text("Введіть назву і ціну: IPA=60 грн/л")

    elif data == "admin_delete" and uid == ADMIN_CHAT_ID:
        context.user_data["admin_action"] = "delete"
        await query.message.reply_text("Введіть назву товару")

    elif data == "back":
        await query.edit_message_text(
            "Оберіть дію:",
            reply_markup=main_menu()
        )

# =====================
# TEXT / CONTACT
# =====================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id

    # ---- ADMIN ----
    if uid == ADMIN_CHAT_ID:
        action = context.user_data.get("admin_action")

        if action == "add":
            name, price = update.message.text.split("=")
            BEER_MENU[name.strip()] = price.strip()
            context.user_data["admin_action"] = None
            await update.message.reply_text("✅ Додано", reply_markup=main_menu())

        elif action == "delete":
            BEER_MENU.pop(update.message.text.strip(), None)
            context.user_data["admin_action"] = None
            await update.message.reply_text("❌ Видалено", reply_markup=main_menu())

    # ---- CLIENT PHONE ----
    if context.user_data.get("await_phone"):
        context.user_data["phone"] = update.message.text
        await finalize_order(update, context)

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("await_phone"):
        context.user_data["phone"] = update.message.contact.phone_number
        await finalize_order(update, context)

# =====================
# FINALIZE ORDER
# =====================

async def finalize_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    cart = context.user_data.get("cart", [])
    phone = context.user_data.get("phone")

    text = "\n".join(cart)

    msg = (
        f"📦 *Нове замовлення*\n"
        f"👤 {user.full_name}\n"
        f"📞 {phone}\n\n"
        f"{text}"
    )

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=msg,
        parse_mode="Markdown"
    )

    context.user_data.clear()
    await update.message.reply_text(
        "✅ Замовлення прийнято!",
        reply_markup=main_menu()
    )

# =====================
# MAIN
# =====================

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT, text_handler))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
