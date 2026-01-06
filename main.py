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

ADMIN_CHAT_ID = 492853177  # ← твій Telegram ID
TOKEN = os.getenv("TOKEN")
DATA_FILE = "data.json"

if not TOKEN:
    raise RuntimeError("ENV VAR TOKEN not found")

# =====================
# LOAD / SAVE DATA
# =====================

def load_data():
    global BEER_MENU, NEW_ITEMS, PROMOTIONS
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            BEER_MENU = data.get("BEER_MENU", {})
            NEW_ITEMS = data.get("NEW_ITEMS", [])
            PROMOTIONS = data.get("PROMOTIONS", [])
    else:
        # Defaults
        global BEER_MENU, NEW_ITEMS, PROMOTIONS
        BEER_MENU = {
            "IPA": "60 грн/л",
            "Лагер": "50 грн/л",
            "Пшеничне": "55 грн/л",
        }
        NEW_ITEMS = ["Медовий Ель", "Темне карамельне"]
        PROMOTIONS = ["-10% на IPA", "3л Лагеру = 4-й безкоштовно"]
        save_data()

def save_data():
    data = {
        "BEER_MENU": BEER_MENU,
        "NEW_ITEMS": NEW_ITEMS,
        "PROMOTIONS": PROMOTIONS
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =====================
# VOLUMES
# =====================

VOLUMES = ["0.5л", "1л", "1.5л", "2л"]

# =====================
# KEYBOARDS
# =====================

def main_menu(user_id: int):
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
    if user_id == ADMIN_CHAT_ID:
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

def delete_menu_keyboard():
    keyboard = [[InlineKeyboardButton(f"❌ {name}", callback_data=f"delete_{name}")] for name in BEER_MENU]
    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)

def delete_promo_keyboard():
    keyboard = [[InlineKeyboardButton(f"❌ {p}", callback_data=f"delete_promo_{i}")] for i,p in enumerate(PROMOTIONS)]
    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)

def delete_new_keyboard():
    keyboard = [[InlineKeyboardButton(f"❌ {n}", callback_data=f"delete_new_{i}")] for i,n in enumerate(NEW_ITEMS)]
    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)

# =====================
# COMMANDS
# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("cart", [])
    await update.message.reply_text(
        "🍻 *Вітаємо у Пивʼярні*\nОберіть дію:",
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
# CALLBACK BUTTONS
# =====================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id

    # ----- CLIENT -----
    if data == "menu":
        text = "\n".join([f"{k} — {v}" for k, v in BEER_MENU.items()])
        await query.edit_message_text(f"🍺 *Меню:*\n\n{text}", parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Назад", callback_data="back")]]))
    elif data == "promo":
        text = "\n".join([f"• {p}" for p in PROMOTIONS])
        await query.edit_message_text(f"🔥 *Акції:*\n\n{text}", parse_mode="Markdown",
                                      reply_markup=main_menu(uid))
    elif data == "new":
        text = "\n".join([f"• {n}" for n in NEW_ITEMS])
        await query.edit_message_text(f"🆕 *Новинки:*\n\n{text}", parse_mode="Markdown",
                                      reply_markup=main_menu(uid))
    elif data == "order":
        buttons = [[InlineKeyboardButton(b, callback_data=f"beer_{b}")] for b in BEER_MENU]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="back")])
        await query.edit_message_text("Оберіть пиво:", reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("beer_"):
        beer = data.replace("beer_", "")
        context.user_data["beer"] = beer
        buttons = [[InlineKeyboardButton(v, callback_data=f"vol_{v}")] for v in VOLUMES]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="order")])
        await query.edit_message_text(f"{beer} — обʼєм:", reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("vol_"):
        volume = data.replace("vol_", "")
        beer = context.user_data["beer"]
        context.user_data.setdefault("cart", []).append(f"{beer} ({volume})")
        await query.edit_message_text("✅ Додано в кошик",
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton("➕ Додати ще", callback_data="order")],
                                          [InlineKeyboardButton("🛒 Кошик", callback_data="cart")]
                                      ]))
    elif data == "cart":
        cart = context.user_data.get("cart", [])
        if not cart:
            await query.edit_message_text("🛒 Кошик порожній", reply_markup=main_menu(uid))
            return
        text = "\n".join([f"• {i}" for i in cart])
        await query.edit_message_text(f"🛒 *Ваш кошик:*\n\n{text}", parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton("✅ Оформити", callback_data="checkout")],
                                          [InlineKeyboardButton("⬅ Назад", callback_data="back")]
                                      ]))
    elif data == "checkout":
        context.user_data["await_phone"] = True
        await query.message.reply_text("📞 Надішліть номер телефону",
                                       reply_markup=ReplyKeyboardMarkup(
                                           [[KeyboardButton("📞 Надіслати номер", request_contact=True)]],
                                           resize_keyboard=True,
                                           one_time_keyboard=True
                                       ))

    # ----- ADMIN -----
    elif uid == ADMIN_CHAT_ID:
        if data == "admin":
            await query.edit_message_text("⚙ *Адмін панель*", parse_mode="Markdown", reply_markup=admin_menu())
        elif data == "admin_add":
            context.user_data["admin_action"] = "add"
            await query.message.reply_text("Введіть: Назва=Ціна")
        elif data == "admin_delete":
            if not BEER_MENU:
                await query.edit_message_text("Меню порожнє", reply_markup=admin_menu())
                return
            await query.edit_message_text("❌ Оберіть товар для видалення:", reply_markup=delete_menu_keyboard())
        elif data.startswith("delete_"):
            item = data.replace("delete_", "")
            if item in BEER_MENU:
                del BEER_MENU[item]
                save_data()
            await query.edit_message_text(f"✅ Товар *{item}* видалено", parse_mode="Markdown", reply_markup=admin_menu())
        elif data == "admin_add_promo":
            context.user_data["admin_action"] = "add_promo"
            await query.message.reply_text("Введіть текст акції для додавання:")
        elif data == "admin_delete_promo":
            if not PROMOTIONS:
                await query.edit_message_text("Акції порожні", reply_markup=admin_menu())
                return
            await query.edit_message_text("❌ Оберіть акцію для видалення:", reply_markup=delete_promo_keyboard())
        elif data.startswith("delete_promo_"):
            index = int(data.replace("delete_promo_", ""))
            if 0 <= index < len(PROMOTIONS):
                removed = PROMOTIONS.pop(index)
                save_data()
                await query.edit_message_text(f"✅ Акцію *{removed}* видалено", parse_mode="Markdown", reply_markup=admin_menu())
        elif data == "admin_add_new":
            context.user_data["admin_action"] = "add_new"
            await query.message.reply_text("Введіть текст новинки для додавання:")
        elif data == "admin_delete_new":
            if not NEW_ITEMS:
                await query.edit_message_text("Новинки порожні", reply_markup=admin_menu())
                return
            await query.edit_message_text("❌ Оберіть новинку для видалення:", reply_markup=delete_new_keyboard())
        elif data.startswith("delete_new_"):
            index = int(data.replace("delete_new_", ""))
            if 0 <= index < len(NEW_ITEMS):
                removed = NEW_ITEMS.pop(index)
                save_data()
                await query.edit_message_text(f"✅ Новинку *{removed}* видалено", parse_mode="Markdown", reply_markup=admin_menu())

    elif data == "back":
        await query.edit_message_text("🍻 *BeerTime*\nОберіть дію:", parse_mode="Markdown",
                                      reply_markup=main_menu(uid))

# =====================
# TEXT / CONTACT
# =====================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text

    # ---- ADMIN ----
    if uid == ADMIN_CHAT_ID:
        action = context.user_data.get("admin_action")
        if action == "add":
            try:
                name, price = text.split("=", 1)
                BEER_MENU[name.strip()] = price.strip()
                save_data()
                context.user_data["admin_action"] = None
                await update.message.reply_text("✅ Товар додано", reply_markup=main_menu(uid))
                return
            except:
                await update.message.reply_text("❌ Формат: Назва=Ціна")
                return
        elif action == "add_promo":
            PROMOTIONS.append(text.strip())
            save_data()
            context.user_data["admin_action"] = None
            await update.message.reply_text("✅ Акція додана", reply_markup=main_menu(uid))
            return
        elif action == "add_new":
            NEW_ITEMS.append(text.strip())
            save_data()
            context.user_data["admin_action"] = None
            await update.message.reply_text("✅ Новинка додана", reply_markup=main_menu(uid))
            return

    # ---- CLIENT PHONE ----
    if context.user_data.get("await_phone"):
        context.user_data["phone"] = text
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
    order_text = "\n".join(cart)

    msg = f"📦 *Нове замовлення*\n👤 {user.full_name}\n📞 {phone}\n\n{order_text}"
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")

    context.user_data.clear()
    await update.message.reply_text("✅ Замовлення прийнято!", reply_markup=main_menu(user.id))

# =====================
# MAIN
# =====================

def main():
    load_data()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
