import os
import openai
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                          filters, CallbackQueryHandler, ContextTypes)
import typing

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

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
        await query.answer()
        if query.data == "help":
            await query.edit_message_text(
                "Я ассистент. Задавай любые вопросы — помогу по учебе, коду, идеям!")
        elif query.data == "ask":
            await query.edit_message_text("Напиши свой вопрос прямо сюда 👇")


# 💬 Обработка обычных сообщений (как запрос в GPT)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_input = update.message.text
    else:
        user_input = ""
    reply = "Произошла неизвестная ошибка."  # Default error message
    try:
        messages: list[ChatCompletionMessageParam] = typing.cast(list[ChatCompletionMessageParam], [
            ChatCompletionSystemMessageParam(role="system", content="Ты дружелюбный Telegram-ассистент."),
            ChatCompletionUserMessageParam(role="user", content=user_input or "")
        ])
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
        )
        reply = response.choices[0].message.content if response.choices else "Не удалось получить ответ от OpenAI."
    except Exception as e:
        reply = f"Ошибка при запросе к GPT: {e}"
    
    if update.message:
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
        app.run_polling()
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")