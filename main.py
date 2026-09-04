import asyncio
import logging
import os
import threading
from flask import Flask
from aiogram import Bot, Dispatcher

# 1. Bot va admin sozlamalari
BOT_TOKEN = "8934015919:AAEYR7gykqYE9oWoHr4_awFLhpf6_0-Ov9o"
SUPER_ADMIN_ID = 5682605205                         
CHANNEL_ID = -1004495936628                         

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 2. Render uxlab qolmasligi uchun Flask server
web_app = Flask(__name__)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@web_app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# Flask'ni parallel (fon) rejimida yurgizamiz
threading.Thread(target=run_flask, daemon=True).start()

# 3. Botni ishga tushirish
async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Eskidan qolib ketgan ulanishlarni tozalaymiz
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Shu yerga o'zingizning handler/routerlaringizni ulasangiz bo'ladi
    # Masalan: dp.include_router(...)
    
    logging.info("Bot polling ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())