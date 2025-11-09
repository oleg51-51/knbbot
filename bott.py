import os
import json
import random
import asyncio
import aiofiles
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.error import Forbidden
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# 🔐 Загрузка токена из .env
load_dotenv()
TOKEN = ("8240784830:AAH4FXWAOGu-17imAZbVno7xbMqLktoISiQ")

if not TOKEN:
    raise ValueError("❌ Токен не найден! Укажи его в .env файле как BOT_TOKEN=...")

# 📁 Файл для данных
DATA_FILE = "data.json"

# 🎮 Игровые элементы
items = {1: "Камень", 2: "Ножницы", 3: "Бумага"}

# Глобальные данные
scores = {}
total_wins = {}


# 🔄 Загрузка данных
async def load_data():
    global scores, total_wins
    if os.path.exists(DATA_FILE):
        try:
            async with aiofiles.open(DATA_FILE, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                scores = data.get("scores", {})
                total_wins = data.get("total_wins", {})
            print("✅ Данные успешно загружены.")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки данных: {e}")
    else:
        print("📂 data.json не найден — будет создан при первой игре.")


# 💾 Сохранение данных
async def save_data():
    try:
        async with aiofiles.open(DATA_FILE, "w", encoding="utf-8") as f:
            data = {"scores": scores, "total_wins": total_wins}
            await f.write(json.dumps(data, ensure_ascii=False, indent=4))
        print("💾 Данные сохранены.")
    except Exception as e:
        print(f"⚠️ Ошибка сохранения: {e}")


# 🏠 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.callback_query.message

    main_menu = [
        [
            InlineKeyboardButton("🎮 Играть", callback_data="menu_play"),
            InlineKeyboardButton("📜 Правила", callback_data="menu_rules"),
        ],
        [
            InlineKeyboardButton("🏆 Топ", callback_data="menu_top"),
            InlineKeyboardButton("ℹ️ Помощь", callback_data="menu_help"),
        ],
    ]
    await message.reply_text(
        "👋 Привет! Это бот *Камень — Ножницы — Бумага*!\n\nВыбери действие 👇",
        reply_markup=InlineKeyboardMarkup(main_menu),
        parse_mode="Markdown",
    )


# 📜 /rules
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📜 *Правила игры:*\n\n"
        "🪨 Камень побеждает Ножницы\n"
        "✂️ Ножницы побеждают Бумагу\n"
        "📄 Бумага побеждает Камень\n\n"
        "🎯 Игра идёт до 3 очков.\n"
        "🏆 Первый, кто набирает 3 — побеждает!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ℹ️ /help
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Команды бота:*\n\n"
        "/start — главное меню\n"
        "/rules — правила\n"
        "/score — текущий счёт\n"
        "/top — топ игроков\n"
        "/help — помощь",
        parse_mode="Markdown",
    )


# 🧮 /score
async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not scores:
        await update.message.reply_text("😴 Пока никто не играл.")
        return

    lines = []
    for user_id, points in scores.items():
        try:
            user = await context.bot.get_chat(int(user_id))
            name = user.first_name or "Неизвестный"
        except (Forbidden, TelegramError):
            name = f"Игрок {user_id}"
        lines.append(f"{name}: {points}/3")

    await update.message.reply_text(
        "🏅 *Текущие очки:*\n" + "\n".join(lines), parse_mode="Markdown"
    )


# 🏆 /top
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not total_wins:
        await update.message.reply_text("💤 Пока никто не побеждал.")
        return

    sorted_wins = sorted(total_wins.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = []
    for i, (user_id, wins) in enumerate(sorted_wins, 1):
        try:
            user = await context.bot.get_chat(int(user_id))
            name = user.first_name or "Неизвестный"
        except:
            name = f"Игрок {user_id}"
        lines.append(f"{i}. {name} — {wins} побед")

    await update.message.reply_text(
        "🏆 *ТОП-10 игроков:*\n" + "\n".join(lines), parse_mode="Markdown"
    )


# ⚔️ Игровая логика
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user_name = query.from_user.first_name or "Игрок"

    # Главное меню
    if query.data == "menu_play" or query.data == "restart":
        keyboard = [
            [
                InlineKeyboardButton("Камень", callback_data="1"),
                InlineKeyboardButton("Ножницы", callback_data="2"),
                InlineKeyboardButton("Бумага", callback_data="3"),
            ]
        ]
        await safe_edit(query, "🎮 Выбери свой ход:", keyboard)
        return

    # Меню — правила, помощь, топ
    if query.data in {"menu_rules", "menu_help", "menu_top"}:
        await handle_menu(query, context)
        return

    # Игровой выбор
    user_choice = int(query.data)
    bot_choice = random.randint(1, 3)
    bot_item = items.get(bot_choice, "???")
    user_item = items.get(user_choice, "???")

    if user_choice == bot_choice:
        result = "🤝 Ничья!"
    elif (
        (user_choice == 1 and bot_choice == 2)
        or (user_choice == 2 and bot_choice == 3)
        or (user_choice == 3 and bot_choice == 1)
    ):
        result = "🎉 Ты победил!"
        scores[user_id] = scores.get(user_id, 0) + 1
    else:
        result = "😤 Бот победил!"

    funny = random.choice(
        [
            "😏 Я читал твои мысли!",
            "😂 Тебе повезло... на этот раз.",
            "🔥 Горячо!",
            "🤖 Мой алгоритм совершенствуется...",
            "💥 БАМ! И снова в точку!",
        ]
    )
    result += f"\n{funny}"

    current_score = scores.get(user_id, 0)
    keyboard = [[InlineKeyboardButton("🔁 Ещё раз!", callback_data="restart")]]
    text = f"🤖 Бот: {bot_item}\n👤 Ты: {user_item}\n\n{result}\n\n📊 Твой счёт: {current_score}/3"

    # Проверяем победу
    if current_score >= 3:
        total_wins[user_id] = total_wins.get(user_id, 0) + 1
        scores[user_id] = 0
        text += f"\n\n🏆 *{user_name} ВЫИГРАЛ МАТЧ 3:0!* 🎉"
        keyboard.append([InlineKeyboardButton("🏆 Топ игроков", callback_data="menu_top")])

    await safe_edit(query, text, keyboard)
    await save_data()


# Безопасное редактирование сообщений
async def safe_edit(query, text, keyboard):
    try:
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
    except TelegramError:
        pass


# Обработка меню-кнопок
async def handle_menu(query, context):
    if query.data == "menu_rules":
        text = (
            "📜 *Правила:*\n\n"
            "Камень ➡️ бьёт Ножницы\n"
            "Ножницы ➡️ режут Бумагу\n"
            "Бумага ➡️ накрывает Камень\n\n"
            "Игра до 3 очков!"
        )
        await safe_edit(query, text, [[InlineKeyboardButton("🎮 Играть", callback_data="menu_play")]])
    elif query.data == "menu_help":
        text = (
            "🤖 *Команды:*\n\n"
            "/start — главное меню\n"
            "/rules — правила\n"
            "/score — мой счёт\n"
            "/top — топ игроков\n"
            "/help — помощь"
        )
        await safe_edit(query, text, [[InlineKeyboardButton("🎮 Играть", callback_data="menu_play")]])
    elif query.data == "menu_top":
        if not total_wins:
            await safe_edit(query, "💤 Пока никто не побеждал.", [[InlineKeyboardButton("🎮 Играть", callback_data="menu_play")]])
            return
        sorted_wins = sorted(total_wins.items(), key=lambda x: x[1], reverse=True)[:10]
        lines = []
        for i, (uid, wins) in enumerate(sorted_wins, 1):
            try:
                user = await context.bot.get_chat(int(uid))
                name = user.first_name or "Неизвестный"
            except:
                name = f"Игрок {uid}"
            lines.append(f"{i}. {name} — {wins} побед")
        await safe_edit(query, "🏆 *ТОП-10 игроков:*\n" + "\n".join(lines),
                        [[InlineKeyboardButton("🎮 Играть", callback_data="menu_play")]])


# 🚀 Основной запуск
async def main():
    print("🚀 Запуск бота...")
    await load_data()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CallbackQueryHandler(play))

    commands = [
        BotCommand("start", "Начать игру"),
        BotCommand("help", "Помощь"),
        BotCommand("rules", "Правила"),
        BotCommand("score", "Мой счёт"),
        BotCommand("top", "Топ игроков"),
    ]
    await app.bot.set_my_commands(commands)

    print("✅ Команды добавлены в меню Telegram.")
    await app.run_polling(drop_pending_updates=True)
    await save_data()
    print("🛑 Бот остановлен.")


if __name__ == "__main__":
    import nest_asyncio
    import asyncio

    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
