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

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Назад", callback_data="back")]])

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

# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🍻 BeerTime",
        reply_markup=main_menu(update.effective_user.id)
    )

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    await update.message.reply_text("⚙ Адмін панель", reply_markup=admin_menu())

# ================= CALLBACKS =================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    # ---------- USER ----------

    if data == "menu":
        text = "\n".join([f"{k} — {v}" for k, v in BEER_MENU.items()])
        await q.edit_message_text(f"🍺 Меню:\n{text}", reply_markup=back_kb())

    elif data == "promo":
        text = "\n".join(PROMOTIONS) or "Немає акцій"
        await q.edit_message_text(f"🔥 Акції:\n{text}", reply_markup=back_kb())

    elif data == "new":
        text = "\n".join(NEW_ITEMS) or "Немає новинок"
        await q.edit_message_text(f"🆕 Новинки:\n{text}", reply_markup=back_kb())

    # ---------- ADMIN ----------

    elif uid == ADMIN_CHAT_ID and data == "admin":
        await q.edit_message_text("⚙ Адмін панель", reply_markup=admin_menu())

    elif uid == ADMIN_CHAT_ID and data == "add_beer":
        context.user_data["state"] = "add_beer"
        await q.edit_message_text("Введи:\nНазва,ціна")

    elif uid == ADMIN_CHAT_ID and data == "del_beer":
        buttons = [
            [InlineKeyboardButton(name, callback_data=f"delbeer_{name}")]
            for name in BEER_MENU
        ]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="admin")])
        await q.edit_message_text("Вибери товар:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("delbeer_") and uid == ADMIN_CHAT_ID:
        name = data.replace("delbeer_", "")
        BEER_MENU.pop(name, None)
        save_data()
        await q.edit_message_text("❌ Видалено", reply_markup=admin_menu())

    elif uid == ADMIN_CHAT_ID and data == "add_promo":
        context.user_data["state"] = "add_promo"
        await q.edit_message_text("Введи текст акції")

    elif uid == ADMIN_CHAT_ID and data == "del_promo":
        buttons = [
            [InlineKeyboardButton(p, callback_data=f"delpromo_{i}")]
            for i, p in enumerate(PROMOTIONS)
        ]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="admin")])
        await q.edit_message_text("Вибери акцію:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("delpromo_") and uid == ADMIN_CHAT_ID:
        PROMOTIONS.pop(int(data.replace("delpromo_", "")))
        save_data()
        await q.edit_message_text("❌ Акцію видалено", reply_markup=admin_menu())

    elif uid == ADMIN_CHAT_ID and data == "add_new":
        context.user_data["state"] = "add_new"
        await q.edit_message_text("Введи новинку")

    elif uid == ADMIN_CHAT_ID and data == "del_new":
        buttons = [
            [InlineKeyboardButton(n, callback_data=f"delnew_{i}")]
            for i, n in enumerate(NEW_ITEMS)
        ]
        buttons.append([InlineKeyboardButton("⬅ Назад", callback_data="admin")])
        await q.edit_message_text("Вибери новинку:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("delnew_") and uid == ADMIN_CHAT_ID:
        NEW_ITEMS.pop(int(data.replace("delnew_", "")))
        save_data()
        await q.edit_message_text("❌ Новинку видалено", reply_markup=admin_menu())

    elif data == "back":
        await q.edit_message_text("🍻 BeerTime", reply_markup=main_menu(uid))

# ================= TEXT HANDLER =================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    state = context.user_data.get("state")
    text = update.message.text

    if state == "add_beer":
        name, price = text.split(",", 1)
        BEER_MENU[name.strip()] = price.strip()
        save_data()

    elif state == "add_promo":
        PROMOTIONS.append(text)
        save_data()

    elif state == "add_new":
        NEW_ITEMS.append(text)
        save_data()

    context.user_data.clear()
    await update.message.reply_text("✅ Готово", reply_markup=admin_menu())

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
