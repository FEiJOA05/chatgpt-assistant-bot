import os
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                          filters, CallbackQueryHandler, ContextTypes)
import typing

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print(f"BOT_TOKEN найден: {'Да' if BOT_TOKEN else 'Нет'}")
print(f"OPENAI_API_KEY найден: {'Да' if OPENAI_API_KEY else 'Нет'}")

if not OPENAI_API_KEY:
    print("⚠️ OPENAI_API_KEY не найден! Бот будет работать без OpenAI.")
    client = None
else:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI клиент инициализирован успешно")
    except Exception as e:
        print(f"❌ Ошибка инициализации OpenAI: {e}")
        client = None

user_memory = {}


# 🟢 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user:
        user_id = update.effective_user.id
        user_memory[user_id] = {"name": update.effective_user.first_name}
        keyboard = [
            [InlineKeyboardButton("💬 Задать вопрос", callback_data="ask")],
            [InlineKeyboardButton("🧠 Помощь", callback_data="help")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text(
                f"Привет, {user_memory[user_id]['name']}! Я твой Telegram GPT-ассистент.",
                reply_markup=reply_markup)
    else:
        return


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        print(f"🔘 Нажата кнопка: {query.data}")
        await query.answer()
        if query.data == "help":
            await query.edit_message_text(
                "Я ассистент. Задавай любые вопросы — помогу по учебе, коду, идеям!")
            print("✅ Показана помощь")
        elif query.data == "ask":
            await query.edit_message_text("Напиши свой вопрос прямо сюда 👇")
            print("✅ Показано приглашение к вопросу")


# 💬 Обработка обычных сообщений (как запрос в GPT)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
        
    user_input = update.message.text or ""
    print(f"📨 Получено сообщение: {user_input[:50]}...")
    
    if not client:
        reply = "❌ OpenAI не настроен. Проверьте OPENAI_API_KEY в Secrets."
        await update.message.reply_text(reply)
        return
    
    reply = "Произошла неизвестная ошибка."
    
    try:
        print("🔄 Отправляю запрос к OpenAI...")
        messages: list[ChatCompletionMessageParam] = typing.cast(list[ChatCompletionMessageParam], [
            ChatCompletionSystemMessageParam(role="system", content="Ты дружелюбный Telegram-ассистент."),
            ChatCompletionUserMessageParam(role="user", content=user_input)
        ])
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        if response.choices and response.choices[0].message.content:
            reply = response.choices[0].message.content
            print("✅ Получен ответ от OpenAI")
        else:
            reply = "Не удалось получить ответ от OpenAI."
            print("❌ Пустой ответ от OpenAI")
            
    except Exception as e:
        reply = f"Ошибка при запросе к GPT: {str(e)}"
        print(f"❌ Ошибка OpenAI: {e}")
    
    await update.message.reply_text(reply)

if __name__ == '__main__':
    if BOT_TOKEN is None:
        raise ValueError("BOT_TOKEN environment variable not set.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                                   handle_message))

    print("Бот запущен...")
    try:
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        if "Conflict" in str(e):
            print("Конфликт: другой экземпляр бота уже запущен.")
            print("Остановите предыдущий экземпляр и попробуйте снова.")
            exit(1)
        else:
            print("Перезапустите бота через несколько секунд.")
            exit(1)