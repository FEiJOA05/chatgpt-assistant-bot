import os
import json
import asyncio
import requests
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

DATA_FILE = "data.json"
#работа с JSON
def load_data():
    global user_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            user_data.update(json.load(f))

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(user_data, f, indent=4)
        
# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("OPENAI_API_KEY")
API_URL = "https://api.groq.com/openai/v1/chat/completions"

if BOT_TOKEN is None:
    raise ValueError("BOT_TOKEN не найден в переменных окружения. Пожалуйста, создайте файл .env и добавьте BOT_TOKEN=ваш_токен")

if API_KEY is None:
    raise ValueError("OPENAI_API_KEY не найден в переменных окружения. Пожалуйста, добавьте OPENAI_API_KEY=ваш_ключ в файл .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Хранилище данных пользователей
user_data = {}
load_data()

def get_user_data(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"goals": [], "chat_history": [], "dialog_mode": False}
    return user_data[user_id]

def get_user_goals(user_id):
    return get_user_data(user_id)["goals"]

def add_user_goal(user_id, goal):
    get_user_data(user_id)["goals"].append(goal)
    save_data()

def add_to_chat_history(user_id, role, message):
    history = get_user_data(user_id)["chat_history"]
    history.append({"role": role, "content": message})
    if len(history) > 20:
        history.pop(0)
    save_data()

def set_dialog_mode(user_id, mode):
    get_user_data(user_id)["dialog_mode"] = mode
    save_data()

def is_dialog_mode(user_id):
    return get_user_data(user_id)["dialog_mode"]

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Мои цели", callback_data="goals")],
        [InlineKeyboardButton(text="📈 Добавить новую цель", callback_data="add_goal")],
        [InlineKeyboardButton(text="💬 Диалог", callback_data="dialog")]
    ])

def ask_ai(question, user_id=None, is_dialog=False):
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        if is_dialog and user_id:
            messages = [{"role": "system", "content": "Ты дружелюбный собеседник. Поддерживай разговор на любые темы, запоминай то, о чем говорили раньше."}]
            messages.extend(get_user_data(user_id)["chat_history"])
            messages.append({"role": "user", "content": question})
        else:
            messages = [
                {"role": "system", "content": "Ты дружелюбный помощник по достижению целей."},
                {"role": "user", "content": question}
            ]

        data = {
            "model": "llama3-70b-8192",
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.7
        }

        response = requests.post(API_URL, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return "Ошибка при обращении к ИИ"
    except Exception as e:
        logging.error(f"Ошибка в ask_ai: {e}")
        return "Произошла ошибка"

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"Привет, {user_name}! 👋\n\nЯ помощник по целям. Могу помочь тебе ставить и отслеживать цели!",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query_handler(lambda c: c.data == "goals")
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

@dp.callback_query_handler(lambda c: c.data == "add_goal")
async def add_goal_prompt(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📈 Напишите вашу новую цель:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back")]
        ])
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "dialog")
async def start_dialog(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    set_dialog_mode(user_id, True)
    await callback.message.edit_text(
        "💬 Режим диалога активирован!\n\nТеперь мы можем обсуждать любые темы. Я буду помнить наш разговор.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back")]
        ])
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back")
async def back_to_main(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    set_dialog_mode(user_id, False)
    user_name = callback.from_user.first_name
    await callback.message.edit_text(
        f"Привет, {user_name}! 👋\n\nЯ помощник по целям. Могу помочь тебе ставить и отслеживать цели!",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.message_handler()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text

    if is_dialog_mode(user_id):
        add_to_chat_history(user_id, "user", user_text)
        response = ask_ai(user_text, user_id, is_dialog=True)
        add_to_chat_history(user_id, "assistant", response)

        await message.answer(
            response,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back")]
            ])
        )
    else:
        if any(word in user_text.lower() for word in ["хочу", "планирую", "цель", "буду", "собираюсь"]):
            add_user_goal(user_id, user_text)
            await message.answer(
                f"✅ Цель добавлена: {user_text}",
                reply_markup=get_main_keyboard()
            )
        else:
            response = ask_ai(user_text)
            await message.answer(response, reply_markup=get_main_keyboard())

logging.info("Программа запущена")

if __name__ == '__main__':
    print("🤖 Бот запущен...")
    executor.start_polling(dp, skip_updates=True)


