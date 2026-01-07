import os
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
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
BEER_MENU = {}
PROMOTIONS = []
NEW_ITEMS = []

# ================= DATA LOAD / SAVE =================

def load_data():
    global BEER_MENU, PROMOTIONS, NEW_ITEMS

    default_data = {
        "BEER_MENU": {
            "IPA": "60 грн/л",
            "Лагер": "50 грн/л"
        },
        "PROMOTIONS": [],
        "NEW_ITEMS": []
    }

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    BEER_MENU = data.get("BEER_MENU", {})
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
        [
            InlineKeyboardButton("🔥 Акції", callback_data="promo"),
            InlineKeyboardButton("🆕 Новинки", callback_data="new")
        ],
        [InlineKeyboardButton("🛒 Замовити", callback_data="order")]
    ]
    if uid == ADMIN_CHAT_ID:
        kb.append([InlineKeyboardButton("⚙ Admin", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Додати товар", callback_data="add_beer")],
        [InlineKeyboardButton("❌ Видалити товар", callback_data="del_beer")],
        [InlineKeyboardButton("➕ Додати акцію", callback_data="add_promo")],
        [InlineKeyboardButton("❌ Видалити акцію", callback_data="del_promo")],
        [InlineKeyboardButton("➕ Додати новинку", callback_data="add_new")],
        [InlineKeyboardButton("❌ Видалити новинку", callback_data="del_new")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back_main")]
    ])

# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["cart"] = []
    await update.message.reply_text(
        "🍻 *BeerTime*\nОберіть дію:",
        parse_mode="Markdown",
        reply_markup=main_menu(update.effective_user.id)
    )

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    await update.message.reply_text(
        "⚙ *Адмін панель*",
        parse_mode="Markdown",
        reply_markup=admin_menu()
    )

# ================= CALLBACKS =================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    # ---------------- BACK ----------------
    if data == "back_main":
        await q.edit_message_text("🍻 *BeerTime*\nОберіть дію:", parse_mode="Markdown",
                                  reply_markup=main_menu(uid))
        return

    # ---------------- MENU / PROMO / NEW ----------------
    if data == "menu":
        text = "\n".join([f"{k} — {v}" for k, v in BEER_MENU.items()]) or "Поки порожньо"
        await q.edit_message_text(text=f"🍺 *Меню:*\n\n{text}",
                                  parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Назад", callback_data="back_main")]]))
        return

    elif data == "promo":
        text = "\n".join(PROMOTIONS) or "Немає акцій"
        await q.edit_message_text(text=f"🔥 *Акції:*\n\n{text}",
                                  parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Назад", callback_data="back_main")]]))
        return

    elif data == "new":
        text = "\n".join(NEW_ITEMS) or "Немає новинок"
        await q.edit_message_text(text=f"🆕 *Новинки:*\n\n{text}",
                                  parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Назад", callback_data="back_main")]]))
        return

    # ---------------- ORDER ----------------
    if data == "order":
        buttons = [[InlineKeyboardButton(b, callback_data=f"beer_{b}")] for b in BEER_MENU]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="back_main")])
        await q.edit_message_text("Оберіть пиво:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    elif data.startswith("beer_"):
        beer = data.replace("beer_", "")
        context.user_data["beer"] = beer
        buttons = [[InlineKeyboardButton(v, callback_data=f"vol_{v}")] for v in VOLUMES]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="order")])
        await q.edit_message_text(f"*{beer}*\nОберіть обʼєм:", parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(buttons))
        return

    elif data.startswith("vol_"):
        volume = data.replace("vol_", "")
        beer = context.user_data.get("beer")
        context.user_data.setdefault("cart", []).append(f"{beer} ({volume})")
        await q.edit_message_text("✅ Додано в кошик",
                                  reply_markup=InlineKeyboardMarkup([
                                      [InlineKeyboardButton("➕ Додати ще", callback_data="order")],
                                      [InlineKeyboardButton("🛒 Кошик", callback_data="cart")],
                                      [InlineKeyboardButton("⬅ Назад", callback_data="back_main")]
                                  ]))
        return

    # ---------------- CART (Rozetka style) ----------------
    if data == "cart":
        cart = context.user_data.get("cart", [])
        if not cart:
            await q.edit_message_text("🛒 Кошик порожній",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Назад", callback_data="back_main")]]))
            return

        kb = [[InlineKeyboardButton(f"❌ {i}", callback_data=f"del_{idx}")] for idx, i in enumerate(cart)]
        kb.append([InlineKeyboardButton("🧹 Очистити кошик", callback_data="cart_clear")])
        kb.append([InlineKeyboardButton("✅ Оформити", callback_data="checkout")])
        kb.append([InlineKeyboardButton("⬅ Назад", callback_data="back_main")])

        text = "\n".join([f"• {i}" for i in cart])
        await q.edit_message_text(f"🛒 *Ваш кошик:*\n\n{text}",
                                  parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(kb))
        return

    elif data.startswith("del_"):
        idx = int(data.replace("del_", ""))
        cart = context.user_data.get("cart", [])
        if 0 <= idx < len(cart):
            cart.pop(idx)
        await callbacks(update, context)
        return

    elif data == "cart_clear":
        context.user_data["cart"] = []
        await q.edit_message_text("🧹 Кошик очищено", reply_markup=main_menu(uid))
        return

    elif data == "checkout":
        context.user_data["await_phone"] = True
        await q.message.reply_text("📞 Введіть номер телефону у форматі +380XXXXXXXXX")
        return

    # ---------------- ADMIN ----------------
    if uid == ADMIN_CHAT_ID:
        if data == "admin":
            await q.edit_message_text("⚙ Адмін панель", reply_markup=admin_menu())
            return
        if data in ["add_beer","del_beer","add_promo","del_promo","add_new","del_new"]:
            context.user_data["admin_action"] = data
            await q.message.reply_text("Введіть текст:")
            return

# ================= TEXT =================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    action = context.user_data.get("admin_action")

    # ----- ADMIN -----
    if uid == ADMIN_CHAT_ID and action:
        if action == "add_beer":
            try:
                name, price = text.split("=", 1)
                BEER_MENU[name.strip()] = price.strip()
            except:
                await update.message.reply_text("❌ Формат: Назва=Ціна")
                return
        elif action == "del_beer":
            BEER_MENU.pop(text.strip(), None)
        elif action == "add_promo":
            PROMOTIONS.append(text)
        elif action == "del_promo" and text in PROMOTIONS:
            PROMOTIONS.remove(text)
        elif action == "add_new":
            NEW_ITEMS.append(text)
        elif action == "del_new" and text in NEW_ITEMS:
            NEW_ITEMS.remove(text)

        save_data()
        context.user_data["admin_action"] = None
        await update.message.reply_text("✅ Готово", reply_markup=main_menu(uid))
        return

    # ----- PHONE INPUT -----
    if context.user_data.get("await_phone"):
        phone = text
        cart = context.user_data.get("cart", [])
        user = update.effective_user

        msg = f"📦 *НОВЕ ЗАМОВЛЕННЯ*\n👤 {user.full_name}\n📞 {phone}\n\n" + "\n".join(cart)
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")

        context.user_data.clear()
        await update.message.reply_text("✅ Замовлення прийнято!", reply_markup=main_menu(uid))

# ================= MAIN =================

def main():
    load_data()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
