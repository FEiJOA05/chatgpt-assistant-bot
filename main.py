
import os
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                          filters, CallbackQueryHandler, ContextTypes)
import typing
import asyncio
import logging

# Включаем логирование для telegram
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
    print("🚀 Получена команда /start")
    if not update.effective_user or not update.message:
        print("❌ Нет пользователя или сообщения")
        return
        
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Пользователь"
    print(f"👤 Пользователь: {user_name} (ID: {user_id})")
    
    user_memory[user_id] = {"name": user_name}
    
    keyboard = [
        [InlineKeyboardButton("💬 Задать вопрос", callback_data="ask")],
        [InlineKeyboardButton("🧠 Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Привет, {user_name}! Я твой Telegram GPT-ассистент.",
        reply_markup=reply_markup
    )
    print("✅ Стартовое сообщение отправлено с кнопками")


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🔔 handle_button вызван!")
    
    if not update.callback_query:
        print("❌ Нет callback_query")
        return
    
    query = update.callback_query
    print(f"🔘 Callback data: '{query.data}'")
    print(f"👤 Пользователь: {query.from_user.first_name if query.from_user else 'Неизвестен'}")
    
    try:
        # Подтверждаем получение callback
        await query.answer()
        print("✅ Callback подтвержден")
        
        if query.data == "help":
            text = "🧠 Я ассистент. Задавай любые вопросы — помогу по учебе, коду, идеям!\n\nОтправь мне любое сообщение, и я отвечу."
            await query.edit_message_text(text=text)
            print("✅ Показана помощь")
            
        elif query.data == "ask":
            text = "💬 Напиши свой вопрос прямо сюда 👇\n\nЯ готов помочь с любыми вопросами!"
            await query.edit_message_text(text=text)
            print("✅ Показано приглашение к вопросу")
            
        else:
            print(f"❓ Неизвестная кнопка: {query.data}")
            await query.answer("Неизвестная команда")
            
    except Exception as e:
        print(f"❌ Ошибка в handle_button: {e}")
        import traceback
        traceback.print_exc()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    user_input = update.message.text
    print(f"📨 Получено сообщение: {user_input[:50]}...")
    
    if not client:
        reply = "❌ OpenAI не настроен. Проверьте OPENAI_API_KEY в Secrets."
        await update.message.reply_text(reply)
        return
    
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


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"❌ Произошла ошибка: {context.error}")
    if isinstance(update, Update) and update.callback_query:
        print("❌ Ошибка связана с callback_query")


if __name__ == '__main__':
    if BOT_TOKEN is None:
        raise ValueError("BOT_TOKEN environment variable not set.")

    print(f"🤖 Инициализация бота с токеном: {BOT_TOKEN[:10]}...")
    
    # Создаем приложение
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    print("📋 Добавляем обработчики...")
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчик ошибок
    app.add_error_handler(error_handler)
    
    print("🚀 Бот запущен и ожидает сообщения...")
    
    try:
        # Используем более простую конфигурацию polling
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        if "Conflict" in str(e):
            print("⚠️ Конфликт: другой экземпляр бота уже запущен.")
            print("Остановите предыдущий экземпляр и попробуйте снова.")
        else:
            print("🔄 Перезапустите бота через несколько секунд.")
