import os
import json
import random
import aiofiles
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CallbackQueryHandler, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ Токен не найден!")




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
        async with aiofiles.open(DATA_FILE, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
            scores = data.get("scores", {})
            total_wins = data.get("total_wins", {})

# 💾 Сохранение данных
async def save_data():
    async with aiofiles.open(DATA_FILE, "w", encoding="utf-8") as f:
        await f.write(json.dumps({"scores": scores, "total_wins": total_wins}, ensure_ascii=False, indent=4))

# 🏠 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    main_menu = [
        [InlineKeyboardButton("🎮 Играть", callback_data="menu_play"),
         InlineKeyboardButton("📜 Правила", callback_data="menu_rules")],
        [InlineKeyboardButton("🏆 Топ", callback_data="menu_top"),
         InlineKeyboardButton("ℹ️ Помощь", callback_data="menu_help")]
    ]
    await update.message.reply_text(
        "👋 Привет! Это бот *Камень — Ножницы — Бумага*!\n\nВыбери действие 👇",
        reply_markup=InlineKeyboardMarkup(main_menu),
        parse_mode="Markdown"
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
        "🤖 *Команды бота:*\n"
        "/start — главное меню\n"
        "/rules — правила\n"
        "/score — текущий счёт\n"
        "/top — топ игроков\n"
        "/help — помощь",
        parse_mode="Markdown"
    )

# 🧮 /score
async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not scores:
        await update.message.reply_text("😴 Пока никто не играл.")
        return
    lines = []
    for user_id, points in scores.items():
        lines.append(f"{user_id}: {points}/3")
    await update.message.reply_text("🏅 *Текущие очки:*\n" + "\n".join(lines), parse_mode="Markdown")

# 🏆 /top
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not total_wins:
        await update.message.reply_text("💤 Пока никто не побеждал.")
        return
    sorted_wins = sorted(total_wins.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = [f"{i+1}. {uid} — {wins} побед" for i, (uid, wins) in enumerate(sorted_wins)]
    await update.message.reply_text("🏆 *ТОП-10 игроков:*\n" + "\n".join(lines), parse_mode="Markdown")

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

    if query.data in {"menu_rules", "menu_help", "menu_top"}:
        await handle_menu(query)
        return

    user_choice = int(query.data)
    bot_choice = random.randint(1, 3)
    bot_item = items.get(bot_choice, "???")
    user_item = items.get(user_choice, "???")

    if user_choice == bot_choice:
        result = "🤝 Ничья!"
    elif (user_choice == 1 and bot_choice == 2) or (user_choice == 2 and bot_choice == 3) or (user_choice == 3 and bot_choice == 1):
        result = "🎉 Ты победил!"
        scores[user_id] = scores.get(user_id, 0) + 1
    else:
        result = "😤 Бот победил!"

    current_score = scores.get(user_id, 0)
    text = f"🤖 Бот: {bot_item}\n👤 Ты: {user_item}\n\n{result}\n\n📊 Твой счёт: {current_score}/3"
    keyboard = [[InlineKeyboardButton("🔁 Ещё раз!", callback_data="restart")]]

    if current_score >= 3:
        total_wins[user_id] = total_wins.get(user_id, 0) + 1
        scores[user_id] = 0
        text += f"\n\n🏆 *{user_name} ВЫИГРАЛ МАТЧ 3:0!* 🎉"
        keyboard.append([InlineKeyboardButton("🏆 Топ игроков", callback_data="menu_top")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    await save_data()

async def handle_menu(query):
    if query.data == "menu_rules":
        text = "📜 *Правила:*\nКамень ➡️ Ножницы\nНожницы ➡️ Бумага\nБумага ➡️ Камень\nИгра до 3 очков!"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Играть", callback_data="menu_play")]]))
    elif query.data == "menu_help":
        text = "🤖 *Команды:*\n/start, /rules, /score, /top, /help"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Играть", callback_data="menu_play")]]))
    elif query.data == "menu_top":
        if not total_wins:
            await query.edit_message_text("💤 Пока никто не побеждал.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Играть", callback_data="menu_play")]]))
            return
        sorted_wins = sorted(total_wins.items(), key=lambda x: x[1], reverse=True)[:10]
        lines = [f"{i+1}. {uid} — {wins} побед" for i, (uid, wins) in enumerate(sorted_wins)]
        await query.edit_message_text("🏆 *ТОП-10 игроков:*\n" + "\n".join(lines),
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Играть", callback_data="menu_play")]]))

# 🔗 FastAPI и webhook
fastapi_app = FastAPI()
bot_app = ApplicationBuilder().token(TOKEN).build()

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("rules", rules))
bot_app.add_handler(CommandHandler("score", score))
bot_app.add_handler(CommandHandler("top", top))
bot_app.add_handler(CommandHandler("help", help_cmd))
bot_app.add_handler(CallbackQueryHandler(play))

@fastapi_app.post(f"/webhook/{TOKEN}")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.update_queue.put(update)
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    import asyncio

    asyncio.get_event_loop().run_until_complete(load_data())

    # Настройка webhook
    bot_app.start_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=TOKEN
    )
    bot_app.bot.set_webhook(f"https://ВАШ_ДОМЕН/render/{TOKEN}")

    # Запуск FastAPI
    uvicorn.run(fastapi_app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))





