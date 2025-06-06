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
    print("🚀 Получена команда /start")
    if update.effective_user:
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "Пользователь"
        print(f"👤 Пользователь: {user_name} (ID: {user_id})")
        
        user_memory[user_id] = {"name": user_name}
        keyboard = [
            [InlineKeyboardButton("💬 Задать вопрос", callback_data="ask")],
            [InlineKeyboardButton("🧠 Помощь", callback_data="help")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text(
                f"Привет, {user_memory[user_id]['name']}! Я твой Telegram GPT-ассистент.",
                reply_markup=reply_markup)
            print("✅ Стартовое сообщение отправлено с кнопками")
        else:
            print("❌ update.message отсутствует")
    else:
        print("❌ update.effective_user отсутствует")
        return


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"🔔 handle_button вызван!")
    print(f"🔍 Update объект: {update}")
    print(f"🔍 Есть ли callback_query: {hasattr(update, 'callback_query') and update.callback_query is not None}")
    
    query = update.callback_query
    if query:
        print(f"🔘 Получен callback_query с данными: '{query.data}'")
        print(f"👤 От пользователя: {query.from_user.first_name if query.from_user else 'Неизвестен'}")
        print(f"📱 ID чата: {query.message.chat.id if query.message else 'Нет сообщения'}")
        
        try:
            # Обязательно отвечаем на callback query
            await query.answer("Обрабатываю...")
            print("✅ query.answer() выполнен")
            
            if query.data == "help":
                new_text = "🧠 Я ассистент. Задавай любые вопросы — помогу по учебе, коду, идеям!\n\nОтправь мне любое сообщение, и я отвечу."
                await query.edit_message_text(text=new_text)
                print("✅ Показана помощь")
            elif query.data == "ask":
                new_text = "💬 Напиши свой вопрос прямо сюда 👇\n\nЯ готов помочь с любыми вопросами!"
                await query.edit_message_text(text=new_text)
                print("✅ Показано приглашение к вопросу")
            else:
                print(f"❓ Неизвестная кнопка: {query.data}")
                await query.answer("Неизвестная команда")
                
        except Exception as e:
            print(f"❌ Ошибка в handle_button: {e}")
            print(f"❌ Тип ошибки: {type(e).__name__}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ callback_query отсутствует в update")
        print(f"❌ Что есть в update: {dir(update)}")


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

# Обработчик для отслеживания всех обновлений
async def log_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📥 Получено обновление: {type(update).__name__}")
    if update.message:
        print(f"📨 Сообщение: {update.message.text}")
    if update.callback_query:
        print(f"🔘 Callback: {update.callback_query.data}")

# Добавляем универсальный обработчик для отладки
async def debug_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"🔍 DEBUG: Получено обновление типа: {type(update).__name__}")
    if update.message:
        print(f"📨 Сообщение: {update.message.text}")
    if update.callback_query:
        print(f"🔘 Callback query: {update.callback_query.data}")
        print(f"👤 От пользователя: {update.callback_query.from_user.first_name if update.callback_query.from_user else 'Неизвестен'}")

if __name__ == '__main__':
    if BOT_TOKEN is None:
        raise ValueError("BOT_TOKEN environment variable not set.")

    print(f"🤖 Инициализация бота с токеном: {BOT_TOKEN[:10]}...")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики в правильном порядке
    print("📋 Добавляем обработчики...")
    
    # 1. Обработчик команд
    app.add_handler(CommandHandler("start", start))
    print("  ✅ CommandHandler для /start добавлен")
    
    # 2. Обработчик кнопок (должен быть перед общим обработчиком сообщений)
    callback_handler = CallbackQueryHandler(handle_button)
    app.add_handler(callback_handler)
    print("  ✅ CallbackQueryHandler для кнопок добавлен")
    
    # 3. Обработчик текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("  ✅ MessageHandler для текста добавлен")
    
    # 4. Универсальный обработчик для отладки (последний)
    from telegram.ext import TypeHandler
    app.add_handler(TypeHandler(Update, debug_handler), group=1)
    print("  ✅ Debug handler добавлен")
    
    print("🚀 Бот запущен и ожидает сообщения...")
    try:
        app.run_polling(drop_pending_updates=True, poll_interval=1.0, timeout=10)
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        if "Conflict" in str(e):
            print("⚠️ Конфликт: другой экземпляр бота уже запущен.")
            print("Остановите предыдущий экземпляр и попробуйте снова.")
            exit(1)
        else:
            print("🔄 Перезапустите бота через несколько секунд.")
            exit(1)