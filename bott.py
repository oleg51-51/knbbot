import os
import json
import random
import aiofiles
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.error import Forbidden, TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# 🔐 Загрузка токена
load_dotenv()
TOKEN = "8240784830:AAH4FXWAOGu-17imAZbVno7xbMqLktoISiQ"  

DATA_FILE = "data.json"
items = {1: "Камень", 2: "Ножницы", 3: "Бумага"}
scores = {}
total_wins = {}

# 🔄 Работа с данными
async def load_data():
    global scores, total_wins
    if os.path.exists(DATA_FILE):
        async with aiofiles.open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.loads(await f.read())
            scores = data.get("scores", {})
            total_wins = data.get("total_wins", {})
        print("✅ Данные загружены.")
    else:
        print("📂 data.json не найден — будет создан.")

async def save_data():
    async with aiofiles.open(DATA_FILE, "w", encoding="utf-8") as f:
        await f.write(json.dumps({"scores": scores, "total_wins": total_wins}, ensure_ascii=False, indent=4))
    print("💾 Данные сохранены.")

# 🏠 Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    main_menu = [
        [InlineKeyboardButton("🎮 Играть", callback_data="menu_play"),
         InlineKeyboardButton("📜 Правила", callback_data="menu_rules")],
        [InlineKeyboardButton("🏆 Топ", callback_data="menu_top"),
         InlineKeyboardButton("ℹ️ Помощь", callback_data="menu_help")]
    ]
    await update.message.reply_text(
        "👋 Привет! Это бот Камень — Ножницы — Бумага!\nВыбери действие 👇",
        reply_markup=InlineKeyboardMarkup(main_menu)
    )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ("📜 Правила:\n"
            "🪨 Камень побеждает Ножницы\n"
            "✂️ Ножницы побеждают Бумагу\n"
            "📄 Бумага побеждает Камень\n"
            "Игра до 3 очков.")
    await update.message.reply_text(text)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — главное меню\n/rules — правила\n/score — текущий счёт\n/top — топ игроков\n/help — помощь"
    )

# ⚔️ Игровая логика
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user_name = query.from_user.first_name or "Игрок"

    if query.data == "menu_play" or query.data == "restart":
        keyboard = [[InlineKeyboardButton("Камень", callback_data="1"),
                     InlineKeyboardButton("Ножницы", callback_data="2"),
                     InlineKeyboardButton("Бумага", callback_data="3")]]
        await query.edit_message_text("🎮 Выбери свой ход:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    user_choice = int(query.data)
    bot_choice = random.randint(1, 3)

    if user_choice == bot_choice:
        result = "🤝 Ничья!"
    elif (user_choice == 1 and bot_choice == 2) or \
         (user_choice == 2 and bot_choice == 3) or \
         (user_choice == 3 and bot_choice == 1):
        result = "🎉 Ты победил!"
        scores[user_id] = scores.get(user_id, 0) + 1
    else:
        result = "😤 Бот победил!"

    funny = random.choice(["😏 Я читал твои мысли!", "😂 Тебе повезло...", "🔥 Горячо!", "🤖 Алгоритм совершенствуется...", "💥 БАМ!"])
    result += f"\n{funny}"

    current_score = scores.get(user_id, 0)
    text = f"🤖 Бот: {items[bot_choice]}\n👤 Ты: {items[user_choice]}\n\n{result}\n\n📊 Твой счёт: {current_score}/3"

    keyboard = [[InlineKeyboardButton("🔁 Ещё раз!", callback_data="restart")]]

    if current_score >= 3:
        total_wins[user_id] = total_wins.get(user_id, 0) + 1
        scores[user_id] = 0
        text += f"\n\n🏆 {user_name} ВЫИГРАЛ МАТЧ 3:0! 🎉"
        keyboard.append([InlineKeyboardButton("🏆 Топ игроков", callback_data="menu_top")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    await save_data()

# 🚀 Запуск
async def main():
    await load_data()
    app = ApplicationBuilder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CallbackQueryHandler(play))

    commands = [
        BotCommand("start", "Начать игру"),
        BotCommand("help", "Помощь"),
        BotCommand("rules", "Правила"),
    ]
    await app.bot.set_my_commands(commands)

    print("🚀 Бот запущен!")
    app.run_polling()  # <-- Блокирует поток, держит Render сервис "живым"

if __name__ == "__main__":
    import nest_asyncio
    import asyncio

    nest_asyncio.apply()
    asyncio.run(main())




