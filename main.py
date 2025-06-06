import os
from openai import OpenAI
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Инициализация OpenAI
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
        
    keyboard = [
        [InlineKeyboardButton("💬 Задать вопрос", callback_data="ask")],
        [InlineKeyboardButton("🧠 Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user_name = update.effective_user.first_name if update.effective_user else "Пользователь"
    
    await update.message.reply_text(
        f"Привет, {user_name}! Я твой Telegram GPT-ассистент.",
        reply_markup=reply_markup
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()

    if query.data == "help":
        text = "🧠 Я ассистент. Задавай любые вопросы — помогу по учебе, коду, идеям!\n\nОтправь мне любое сообщение, и я отвечу."
    elif query.data == "ask":
        text = "💬 Напиши свой вопрос прямо сюда 👇\n\nЯ готов помочь с любыми вопросами!"
    else:
        text = "Неизвестная команда"

    await query.edit_message_text(text=text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_input = update.message.text

    if not client:
        await update.message.reply_text("❌ OpenAI не настроен. Проверьте OPENAI_API_KEY в Secrets.")
        return

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты дружелюбный Telegram-ассистент."},
                {"role": "user", "content": user_input}
            ],
            max_tokens=500,
            temperature=0.7
        )

        reply = response.choices[0].message.content if response.choices else "Не удалось получить ответ"

    except Exception as e:
        reply = f"Ошибка: {str(e)}"

    await update.message.reply_text(reply)

if __name__ == '__main__':
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в переменных окружения")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    app.run_polling(drop_pending_updates=True)