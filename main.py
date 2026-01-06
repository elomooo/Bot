import os
import json
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

ADMIN_CHAT_ID = 492853177
TOKEN = os.getenv("TOKEN")
DATA_FILE = "data.json"

if not TOKEN:
    raise RuntimeError("ENV VAR TOKEN not found")

# =====================
# LOAD / SAVE DATA
# =====================

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "BEER_MENU": BEER_MENU,
            "NEW_ITEMS": NEW_ITEMS,
            "PROMOTIONS": PROMOTIONS
        }, f, ensure_ascii=False, indent=2)

def load_data():
    global BEER_MENU, NEW_ITEMS, PROMOTIONS

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            BEER_MENU = data.get("BEER_MENU", {})
            NEW_ITEMS = data.get("NEW_ITEMS", [])
            PROMOTIONS = data.get("PROMOTIONS", [])
    else:
        BEER_MENU = {
            "IPA": "60 грн/л",
            "Лагер": "50 грн/л",
            "Пшеничне": "55 грн/л",
        }
        NEW_ITEMS = ["Медовий Ель", "Темне карамельне"]
        PROMOTIONS = ["-10% на IPA", "3л Лагеру = 4-й безкоштовно"]
        save_data()

# =====================
# CONSTANTS
# =====================

VOLUMES = ["0.5л", "1л", "1.5л", "2л"]

# =====================
# KEYBOARDS
# =====================

def main_menu(uid):
    keyboard = [
        [
            InlineKeyboardButton("🍺 Меню", callback_data="menu"),
            InlineKeyboardButton("🔥 Акції", callback_data="promo"),
        ],
        [
            InlineKeyboardButton("🆕 Новинки", callback_data="new"),
            InlineKeyboardButton("🛒 Кошик", callback_data="cart"),
        ],
        [
            InlineKeyboardButton("🛒 Замовити", callback_data="order"),
        ]
    ]
    if uid == ADMIN_CHAT_ID:
        keyboard.append([InlineKeyboardButton("⚙ Admin", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Додати товар", callback_data="admin_add")],
        [InlineKeyboardButton("❌ Видалити товар", callback_data="admin_delete")],
        [InlineKeyboardButton("➕ Додати акцію", callback_data="admin_add_promo")],
        [InlineKeyboardButton("❌ Видалити акцію", callback_data="admin_delete_promo")],
        [InlineKeyboardButton("➕ Додати новинку", callback_data="admin_add_new")],
        [InlineKeyboardButton("❌ Видалити новинку", callback_data="admin_delete_new")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Назад", callback_data="back")]])

# =====================
# COMMANDS
# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("cart", [])
    await update.message.reply_text(
        "🍻 *BeerTime*\nОберіть дію:",
        parse_mode="Markdown",
        reply_markup=main_menu(update.effective_user.id)
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    await update.message.reply_text(
        "⚙ *Адмін панель*",
        parse_mode="Markdown",
        reply_markup=admin_menu()
    )

# =====================
# CALLBACKS
# =====================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id

    # ---------- MENU / PROMO / NEW (DELETE + SEND) ----------

    if data == "menu":
        try:
            await query.message.delete()
        except:
            pass

        text = "\n".join([f"{k} — {v}" for k, v in BEER_MENU.items()])
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🍺 *Меню:*\n\n{text}",
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )

    elif data == "promo":
        try:
            await query.message.delete()
        except:
            pass

        text = "\n".join([f"• {p}" for p in PROMOTIONS])
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🔥 *Акції:*\n\n{text}",
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )

    elif data == "new":
        try:
            await query.message.delete()
        except:
            pass

        text = "\n".join([f"• {n}" for n in NEW_ITEMS])
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🆕 *Новинки:*\n\n{text}",
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )

    # ---------- ORDER FLOW ----------

    elif data == "order":
        buttons = [[InlineKeyboardButton(b, callback_data=f"beer_{b}")] for b in BEER_MENU]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="back")])
        await query.edit_message_text("Оберіть пиво:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("beer_"):
        context.user_data["beer"] = data.replace("beer_", "")
        buttons = [[InlineKeyboardButton(v, callback_data=f"vol_{v}")] for v in VOLUMES]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="order")])
        await query.edit_message_text("Оберіть обʼєм:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("vol_"):
        item = f"{context.user_data['beer']} ({data.replace('vol_', '')})"
        context.user_data.setdefault("cart", []).append(item)
        await query.edit_message_text(
            "✅ Додано в кошик",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Додати ще", callback_data="order")],
                [InlineKeyboardButton("🛒 Кошик", callback_data="cart")]
            ])
        )

    elif data == "cart":
        try:
            await query.message.delete()
        except:
            pass

        cart = context.user_data.get("cart", [])
        if not cart:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="🛒 Кошик порожній",
                reply_markup=main_menu(uid)
            )
            return

        text = "\n".join([f"• {i}" for i in cart])
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🛒 *Ваш кошик:*\n\n{text}",
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

    elif uid == ADMIN_CHAT_ID and data == "admin":
        await query.edit_message_text("⚙ *Адмін панель*", parse_mode="Markdown", reply_markup=admin_menu())

    # ---------- BACK (UNIVERSAL) ----------

    elif data == "back":
        try:
            await query.message.delete()
        except:
            pass

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🍻 *BeerTime*\nОберіть дію:",
            parse_mode="Markdown",
            reply_markup=main_menu(uid)
        )

# =====================
# MAIN
# =====================

def main():
    load_data()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()

if __name__ == "__main__":
    main()
