import asyncio
import html
import logging
import os
import re
import threading

from flask import Flask
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    BotCommandScopeDefault
)

# Ma'lumotlar bazasini import qilamiz
from database import db

# ---------------------------------------------------------
# 1. Muhit o'zgaruvchilari va O'zgarmaslar
# ---------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8934015919:AAHNz8B4LoDT5QPlcCD4AvZZFpBootHkJuk")
SUPER_ADMIN_ID = int(os.environ.get("SUPER_ADMIN_ID", 5682605205))
# Render'da -100 bilan boshlanuvchi to'liq 13 xonali ID o'rnatilgan bo'lsa, o'shani oladi
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", -1004495936628))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------------------------------------------------------
# 2. Key-Alive Flask Server (Render o'chib qolmasligi uchun)
# ---------------------------------------------------------
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

# ---------------------------------------------------------
# 3. Tugmalar va Menyu
# ---------------------------------------------------------
def get_main_keyboard(user_id: int):
    buttons = [
        [KeyboardButton(text="📚 Katalog"), KeyboardButton(text="🔍 Qidirish")]
    ]
    if user_id == SUPER_ADMIN_ID:
        buttons.append([KeyboardButton(text="➕ Kitob qo'shish"), KeyboardButton(text="⚙️ Admin Panel")])
        
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ---------------------------------------------------------
# 4. Handler'lar (Buyruqlar va xabarlar)
# ---------------------------------------------------------
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    kb = get_main_keyboard(message.from_user.id)
    await message.answer(
        f"Assalomu alaykum, <b>{html.escape(message.from_user.full_name)}</b>!\n"
        f"Kutubxona botiga xush kelibsiz. Kerakli bo'limni tanlang:",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.message(F.text == "📚 Katalog")
async def catalog_handler(message: types.Message):
    await message.answer("Katalog bo'limi tanlandi. Kitoblar ro'yxati shakllantirilmoqda...")

@dp.message(F.text == "🔍 Qidirish")
async def search_handler(message: types.Message):
    await message.answer("Qidirmoqchi bo'lgan kitob nomini yoki muallifini kiriting:")

@dp.message(F.text == "➕ Kitob qo'shish")
async def add_book_handler(message: types.Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("Sizda bu bo'limdan foydalanish huquqi yo'q.")
        return
    await message.answer("Yangi kitob faylini va ma'lumotlarini yuboring.")

@dp.message(F.text == "⚙️ Admin Panel")
async def admin_panel_handler(message: types.Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("Sizda bu bo'limdan foydalanish huquqi yo'q.")
        return
    await message.answer("Admin panelga xush kelibsiz. Boshqaruv menyusi:")

# Boshqa barcha matnli xabarlarni ushlab qoluvchi catch-all handler (Update is not handled xatosini oldini oladi)
@dp.message(F.text)
async def default_text_handler(message: types.Message):
    await message.answer(f"Siz yubordingiz: {message.text}\nKerakli bo'limni pastdagi menyudan tanlang.")

# ---------------------------------------------------------
# 5. Botni ishga tushirish
# ---------------------------------------------------------
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    
    # Flask serverni fonda yoqish
    keep_alive()
    
    # Webhook ziddiyatlarini tozalab, pollingni boshlash
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot polling ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())