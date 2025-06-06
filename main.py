
import os
import asyncio
import requests
import openai
from openai import OpenAI
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = "https://api.groq.com/openai/v1"
openai.api_base = OPENAI_API_BASE

# Инициализация OpenAI
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE) if OPENAI_API_KEY else None

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

def ask_groq(user_input):
    try:
        url = f"{OPENAI_API_BASE}/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "mixtral-8x7b-32768",
            "messages": [
                {"role": "system", "content": "Ты дружелюбный Telegram-ассистент."},
                {"role": "user", "content": user_input}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }

        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        
        # Проверяем успешность запроса
        if response.status_code != 200:
            return f"Ошибка API: {response.status_code} - {response_data.get('error', {}).get('message', 'Неизвестная ошибка')}"
        
        # Проверяем наличие choices в ответе
        if "choices" not in response_data or not response_data["choices"]:
            return f"Ошибка: Неожиданный формат ответа API - {response_data}"
            
        return response_data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Ошибка: {str(e)}"

@dp.message(F.text)
async def handle_message(message: types.Message):
    if not message.text:
        return

    user_input = message.text

    if not OPENAI_API_KEY:
        await message.answer("❌ OpenAI не настроен. Проверьте OPENAI_API_KEY в Secrets.")
        return

    reply = ask_groq(user_input)
    await message.answer(reply)

async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в переменных окружения")
    
    print("Бот запущен...")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
