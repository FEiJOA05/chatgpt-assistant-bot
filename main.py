
import os
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Инициализация OpenAI
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Задать вопрос", callback_data="ask")],
        [InlineKeyboardButton(text="🧠 Помощь", callback_data="help")]
    ])
    
    user_name = message.from_user.first_name if message.from_user else "Пользователь"
    
    await message.answer(
        f"Привет, {user_name}! Я твой Telegram GPT-ассистент.",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.in_(["help", "ask"]))
async def handle_buttons(callback: types.CallbackQuery):
    if callback.data == "help":
        text = "🧠 Я ассистент. Задавай любые вопросы — помогу по учебе, коду, идеям!\n\nОтправь мне любое сообщение, и я отвечу."
    elif callback.data == "ask":
        text = "💬 Напиши свой вопрос прямо сюда 👇\n\nЯ готов помочь с любыми вопросами!"
    else:
        text = "Неизвестная команда"
    
    await callback.message.edit_text(text)
    await callback.answer()

@dp.message(F.text)
async def handle_message(message: types.Message):
    if not message.text:
        return

    user_input = message.text

    if not client:
        await message.answer("❌ OpenAI не настроен. Проверьте OPENAI_API_KEY в Secrets.")
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

    await message.answer(reply)

async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в переменных окружения")
    
    print("Бот запущен...")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
