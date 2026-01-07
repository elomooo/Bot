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

# ================= CONFIG =================

TOKEN = os.getenv("TOKEN")
ADMIN_CHAT_ID = 492853177
DATA_FILE = "data.json"

if not TOKEN:
    raise RuntimeError("TOKEN not set")

# ================= DATA =================

VOLUMES = ["0.5л", "1л", "1.5л", "2л"]

def load_data():
    global BEER_MENU, PROMOTIONS, NEW_ITEMS

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    BEER_MENU = data.get("BEER_MENU", {
        "IPA": "60 грн/л",
        "Лагер": "50 грн/л"
    })
    PROMOTIONS = data.get("PROMOTIONS", [])
    NEW_ITEMS = data.get("NEW_ITEMS", [])

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "BEER_MENU": BEER_MENU,
            "PROMOTIONS": PROMOTIONS,
            "NEW_ITEMS": NEW_ITEMS
        }, f, ensure_ascii=False, indent=2)

# ================= KEYBOARDS =================

def main_menu(uid):
    kb = [
        [InlineKeyboardButton("🍺 Меню", callback_data="menu")],
        [InlineKeyboardButton("🔥 Акції", callback_data="promo"),
         InlineKeyboardButton("🆕 Новинки", callback_data="new")],
        [InlineKeyboardButton("🛒 Замовити", callback_data="order")]
    ]
    if uid == ADMIN_CHAT_ID:
        kb.append([InlineKeyboardButton("⚙ Admin", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

def back_to_main(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅ Назад", callback_data="back")]
    ])

# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["cart"] = []
    await update.message.reply_text(
        "🍻 BeerTime",
        reply_markup=main_menu(update.effective_user.id)
    )

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    await update.message.reply_text("⚙ Адмін панель", reply_markup=admin_menu())

# ================= ADMIN KEYBOARD =================

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Додати товар", callback_data="add_beer")],
        [InlineKeyboardButton("❌ Видалити товар", callback_data="del_beer")],
        [InlineKeyboardButton("➕ Додати акцію", callback_data="add_promo")],
        [InlineKeyboardButton("❌ Видалити акцію", callback_data="del_promo")],
        [InlineKeyboardButton("➕ Додати новинку", callback_data="add_new")],
        [InlineKeyboardButton("❌ Видалити новинку", callback_data="del_new")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back")]
    ])

# ================= CALLBACKS =================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    # ---------- USER ----------

    if data == "menu":
        text = "\n".join([f"{k} — {v}" for k, v in BEER_MENU.items()])
        await q.edit_message_text(f"🍺 Меню:\n{text}", reply_markup=back_to_main(uid))

    elif data == "promo":
        text = "\n".join(PROMOTIONS) or "Немає акцій"
        await q.edit_message_text(f"🔥 Акції:\n{text}", reply_markup=back_to_main(uid))

    elif data == "new":
        text = "\n".join(NEW_ITEMS) or "Немає новинок"
        await q.edit_message_text(f"🆕 Новинки:\n{text}", reply_markup=back_to_main(uid))

    # ---------- ORDER FLOW ----------

    elif data == "order":
        buttons = [
            [InlineKeyboardButton(name, callback_data=f"beer_{name}")]
            for name in BEER_MENU
        ]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="back")])
        await q.edit_message_text("Оберіть пиво:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("beer_"):
        beer = data.replace("beer_", "")
        context.user_data["selected_beer"] = beer

        buttons = [
            [InlineKeyboardButton(v, callback_data=f"vol_{v}")]
            for v in VOLUMES
        ]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="order")])
        await q.edit_message_text(
            f"{beer}\nОберіть обʼєм:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("vol_"):
        volume = data.replace("vol_", "")
        beer = context.user_data.get("selected_beer")

        context.user_data.setdefault("cart", []).append(f"{beer} ({volume})")

        await q.edit_message_text(
            "✅ Додано в кошик",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Додати ще", callback_data="order")],
                [InlineKeyboardButton("🛒 Кошик", callback_data="cart")],
                [InlineKeyboardButton("⬅ Назад", callback_data="back")]
            ])
        )

    elif data == "cart":
        cart = context.user_data.get("cart", [])
        if not cart:
            await q.edit_message_text("🛒 Кошик порожній", reply_markup=back_to_main(uid))
            return

        text = "\n".join([f"• {i}" for i in cart])
        await q.edit_message_text(
            f"🛒 Ваш кошик:\n{text}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Оформити", callback_data="checkout")],
                [InlineKeyboardButton("⬅ Назад", callback_data="back")]
            ])
        )

    elif data == "checkout":
        context.user_data["await_phone"] = True
        await q.message.reply_text(
            "📞 Надішліть номер телефону",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📞 Надіслати номер", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )

    # ---------- ADMIN ----------

    elif uid == ADMIN_CHAT_ID and data == "admin":
        await q.edit_message_text("⚙ Адмін панель", reply_markup=admin_menu())

    elif data == "back":
        await q.edit_message_text("🍻 BeerTime", reply_markup=main_menu(uid))

# ================= CONTACT =================

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("await_phone"):
        return

    phone = update.message.contact.phone_number
    cart = context.user_data.get("cart", [])
    user = update.effective_user

    text = "\n".join(cart)

    msg = (
        f"📦 НОВЕ ЗАМОВЛЕННЯ\n"
        f"👤 {user.full_name}\n"
        f"📞 {phone}\n\n"
        f"{text}"
    )

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=msg
    )

    context.user_data.clear()
    await update.message.reply_text(
        "✅ Замовлення прийнято!",
        reply_markup=main_menu(user.id)
    )

# ================= MAIN =================

def main():
    load_data()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
