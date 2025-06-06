
import os
import asyncio
import requests
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("OPENAI_API_KEY")
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище данных пользователей (в реальном проекте используйте базу данных)
user_data = {}

def get_user_goals(user_id):
    """Получить цели пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {"goals": []}
    return user_data[user_id]["goals"]

def add_user_goal(user_id, goal):
    """Добавить цель пользователю"""
    if user_id not in user_data:
        user_data[user_id] = {"goals": []}
    user_data[user_id]["goals"].append(goal)

def get_main_keyboard():
    """Основная клавиатура"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Мои цели", callback_data="goals")],
        [InlineKeyboardButton(text="📈 Добавить новую цель", callback_data="add_goal")]
    ])

def ask_ai(question):
    """Запрос к ИИ"""
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama3-70b-8192",
            "messages": [
                {"role": "system", "content": "Ты дружелюбный помощник по достижению целей."},
                {"role": "user", "content": question}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        response = requests.post(API_URL, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return "Ошибка при обращении к ИИ"
    except:
        return "Произошла ошибка"

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"Привет, {user_name}! 👋\n\nЯ помощник по целям. Могу помочь тебе ставить и отслеживать цели!",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(F.data == "goals")
async def show_goals(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    goals = get_user_goals(user_id)
    
    if not goals:
        text = "У вас пока нет целей 🫥"
    else:
        text = "🎯 Ваши цели:\n\n"
        for i, goal in enumerate(goals, 1):
            text += f"{i}. {goal}\n"
    
    await callback.message.edit_text(text, reply_markup=get_main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "add_goal")
async def add_goal_prompt(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📈 Напишите вашу новую цель:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "back")
async def back_to_main(callback: types.CallbackQuery):
    user_name = callback.from_user.first_name
    await callback.message.edit_text(
        f"Привет, {user_name}! 👋\n\nЯ помощник по целям. Могу помочь тебе ставить и отслеживать цели!",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text
    
    # Если сообщение начинается с определенных слов, считаем это целью
    if any(word in user_text.lower() for word in ["хочу", "планирую", "цель", "буду", "собираюсь"]):
        add_user_goal(user_id, user_text)
        await message.answer(
            f"✅ Цель добавлена: {user_text}",
            reply_markup=get_main_keyboard()
        )
    else:
        # Обычный вопрос к ИИ
        response = ask_ai(user_text)
        await message.answer(response, reply_markup=get_main_keyboard())

async def main():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
