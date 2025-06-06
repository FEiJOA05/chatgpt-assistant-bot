import os
import asyncio
import requests
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Настройки
load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Данные пользователей
users = {}

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {"goals": [], "history": [], "dialog": False}
    return users[user_id]

def ask_ai(text, user_id=None):
    try:
        user = get_user(user_id) if user_id else None

        if user and user["dialog"]:
            messages = [{"role": "system", "content": "Ты дружелюбный собеседник."}]
            messages.extend(user["history"][-10:])  # Последние 10 сообщений
            messages.append({"role": "user", "content": text})
        else:
            messages = [
                {"role": "system", "content": "Ты помощник по целям."},
                {"role": "user", "content": text}
            ]

        response = requests.post("https://api.groq.com/openai/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}", "Content-Type": "application/json"},
            json={"model": "llama3-70b-8192", "messages": messages, "max_tokens": 500}
        )

        return response.json()["choices"][0]["message"]["content"]
    except:
        return "Ошибка при обращении к ИИ"

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Мои цели", callback_data="goals")],
        [InlineKeyboardButton(text="📈 Добавить цель", callback_data="add_goal")],
        [InlineKeyboardButton(text="💬 Диалог", callback_data="dialog")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(f"Привет, {message.from_user.first_name}! 👋\n\nЯ помощник по целям!", reply_markup=main_menu())

@dp.callback_query(F.data == "goals")
async def show_goals(call: types.CallbackQuery):
    goals = get_user(call.from_user.id)["goals"]
    text = "У вас пока нет целей 🫥" if not goals else "🎯 Ваши цели:\n\n" + "\n".join(f"{i}. {goal}" for i, goal in enumerate(goals, 1))
    await call.message.edit_text(text, reply_markup=main_menu())

@dp.callback_query(F.data == "add_goal")
async def add_goal(call: types.CallbackQuery):
    await call.message.edit_text("📈 Напишите вашу новую цель:", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back")]]))

@dp.callback_query(F.data == "dialog")
async def dialog(call: types.CallbackQuery):
    get_user(call.from_user.id)["dialog"] = True
    await call.message.edit_text("💬 Режим диалога активирован!", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back")]]))

@dp.callback_query(F.data == "back")
async def back(call: types.CallbackQuery):
    get_user(call.from_user.id)["dialog"] = False
    await call.message.edit_text(f"Привет, {call.from_user.first_name}! 👋\n\nЯ помощник по целям!", reply_markup=main_menu())

@dp.message(F.text)
async def handle_text(message: types.Message):
    user = get_user(message.from_user.id)
    text = message.text

    if user["dialog"]:
        # Режим диалога
        user["history"].append({"role": "user", "content": text})
        response = ask_ai(text, message.from_user.id)
        user["history"].append({"role": "assistant", "content": response})
        await message.answer(response, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back")]]))
    else:
        # Обычный режим
        if any(word in text.lower() for word in ["хочу", "планирую", "цель", "буду", "собираюсь"]):
            user["goals"].append(text)
            await message.answer(f"✅ Цель добавлена: {text}", reply_markup=main_menu())
        else:
            response = ask_ai(text)
            await message.answer(response, reply_markup=main_menu())

async def main():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == '__main__':
    asyncio.run(main())