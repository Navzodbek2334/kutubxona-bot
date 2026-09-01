import asyncio
import logging
import os
import threading
from flask import Flask
from aiogram import Bot, Dispatcher

# 1. Muhit o'zgaruvchilari
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8934015919:AAEYR7gykqYE9oWoHr4_awFLhpf6_0-Ov9o")
SUPER_ADMIN_ID = 5682605205                         
CHANNEL_ID = -1004495936628                        

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 2. Flask server
web_app = Flask(__name__)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@web_app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

# Flask'ni dastur boshlanishi bilanoq fonda yurgizamiz
keep_alive()

# 3. Asosiy Bot logikasi
async def main():
    logging.basicConfig(level=logging.INFO)
    
    # MUHIM: Bu yerda barcha handler/routerlaringiz ulangan bo'lishi kerak!
    # Masalan: dp.include_router(start_router)
    
    # Eskidan qolib ketgan webhooklarni tozalaymiz
    await bot.delete_webhook(drop_pending_updates=True)
    
    logging.info("Bot polling rejimi ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

ADMIN_NAV_BUTTONS = ["📚 Katalog", "📥 Kitob qo'shish", "⚙️ Boshqaruv", "📊 Statistika", "🔍 Qidirish"]
USER_NAV_BUTTONS = ["📚 Katalog", "🔍 Qidirish"]

class AdminState(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_reply = State()
    waiting_for_edit_cat_name = State()
    waiting_for_book_file = State()
    waiting_for_book_title = State()
    waiting_for_part_name = State()
    waiting_for_book_category = State()
    waiting_for_search_query = State()
    waiting_for_edit_book_title = State()
    waiting_for_edit_book_part = State()
    waiting_for_new_book_file = State()
    waiting_for_help_request = State()
    waiting_for_new_admin_id = State()

class TextNotInNav(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.text not in (ADMIN_NAV_BUTTONS + USER_NAV_BUTTONS)

def get_admin_menu():
    kb = [
        [KeyboardButton(text="📚 Katalog"), KeyboardButton(text="🔍 Qidirish")],
        [KeyboardButton(text="📥 Kitob qo'shish"), KeyboardButton(text="⚙️ Boshqaruv")],
        [KeyboardButton(text="📊 Statistika")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_user_menu():
    kb = [
        [KeyboardButton(text="📚 Katalog"), KeyboardButton(text="🔍 Qidirish")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")]
    ])

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni qayta ishga tushirish 🔄"),
        BotCommand(command="catalog", description="Kitoblar katalogi 📚"),
        BotCommand(command="search", description="Kitob qidirish 🔍"),
        BotCommand(command="help", description="Yordam va adminga murojaat ℹ️"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    db.add_user(user.id, user.full_name, user.username)
    
    if user.id == SUPER_ADMIN_ID and not db.is_admin(user.id):
        db.add_admin(user.id, role="super_admin")
    
    if db.is_admin(user.id):
        await message.answer("Assalomu alaykum! Qo‘qon shahar 4-son texnikumi kutubxona tizimi (Admin panel) 📚", reply_markup=get_admin_menu())
    else:
        await message.answer("Assalomu alaykum! Qo‘qon shahar 4-son texnikumi elektron kutubxona botiga xush kelibsiz! 📚", reply_markup=get_user_menu())

@dp.message(Command("catalog"))
async def cmd_catalog(message: types.Message, state: FSMContext):
    await state.clear()
    await render_categories(message)

@dp.message(Command("search"))
async def cmd_search(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Qidirmoqchi bo'lgan kitob nomini kiriting:", reply_markup=get_cancel_kb())
    await state.set_state(AdminState.waiting_for_search_query)

# --- HELP BO'LIMI VA ADMINGA MUROJAAT ---
@dp.message(Command("help"))
async def cmd_help(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Adminga murojaat qilish", callback_data="send_help_request")]
    ])
    await message.answer(
        "ℹ️ **Qo‘qon shahar 4-son texnikumi kutubxona boti**\n\n"
        "Bot orqali kerakli elektron kitoblar va o'quv materiallarini topishingiz va yuklab olishingiz mumkin.\n"
        "Savol yoki takliflaringiz bo'lsa, quyidagi tugma orqali adminga murojaat yo'llashingiz mumkin:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "send_help_request")
async def start_help_request(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_help_request)
    await call.message.edit_text(
        "✍️ Adminga yubormoqchi bo'lgan murojaatingizni (savol yoki taklifingizni) yozib qoldiring:",
        reply_markup=get_cancel_kb()
    )
    await call.answer()

import html
import re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. TELEGRAM REPLY (ОТВЕТИТЬ) ORQALI JAVOB BERISH ---
# (Ushbu handler eng tepada turishi shart!)
@dp.message(F.reply_to_message)
async def handle_telegram_reply(message: types.Message, state: FSMContext):
    if not db.is_admin(message.from_user.id):
        return

    # Bekor qilish tugmasi bosilgan bo'lsa
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Amaliyot bekor qilindi.", reply_markup=get_admin_menu())
        return

    original_text = message.reply_to_message.text or message.reply_to_message.caption or ""
    
    # ID ni xabar matnidan qidirish
    match = re.search(r"\(ID:\s*<code>(\d+)</code>\)", original_text) or re.search(r"\(ID:\s*(\d+)\)", original_text)
    if not match:
        return
    
    target_user_id = match.group(1)
    safe_reply = html.escape(message.text)
    
    user_msg = (
        f"🔔 <b>Murojaatingizga admindan javob keldi:</b>\n\n"
        f"💬 {safe_reply}"
    )
    
    try:
        await bot.send_message(chat_id=int(target_user_id), text=user_msg, parse_mode="HTML")
        await message.answer("✅ Javobingiz foydalanuvchiga muvaffaqiyatli yetkazildi!", reply_markup=get_admin_menu())
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Javob yuborishda xatolik: {e}", reply_markup=get_admin_menu())


# --- 2. MUROJAATNI ADMINGA YUBORISH ---
@dp.message(AdminState.waiting_for_help_request)
async def process_help_request(message: types.Message, state: FSMContext):
    if message.text in (ADMIN_NAV_BUTTONS + USER_NAV_BUTTONS) or message.text == "❌ Bekor qilish":
        await state.clear()
        is_admin = db.is_admin(message.from_user.id)
        await message.answer("❌ Murojaat yuborish bekor qilindi.", reply_markup=get_admin_menu() if is_admin else get_user_menu())
        return

    user = message.from_user
    safe_name = html.escape(user.full_name)
    safe_text = html.escape(message.text)
    username_str = f"@{user.username}" if user.username else "Mavjud emas"

    raw_admins = db.get_all_admins()
    SUPER_ADMIN_ID = 5682605205  
    
    admin_ids = set([SUPER_ADMIN_ID])
    if raw_admins:
        for item in raw_admins:
            admin_ids.add(item[0] if isinstance(item, (tuple, list)) else item)

    admin_msg = (
        f"📩 <b>Yangi murojaat!</b>\n\n"
        f"👤 <b>Yuboruvchi:</b> {safe_name} (ID: <code>{user.id}</code>)\n"
        f"🔗 <b>Username:</b> {username_str}\n\n"
        f"💬 <b>Murojaat matni:</b>\n{safe_text}"
    )
    
    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Javob berish", callback_data=f"reply_to_{user.id}")]
    ])
    
    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=int(admin_id), text=admin_msg, parse_mode="HTML", reply_markup=reply_kb)
        except Exception as e:
            logging.error(f"❌ Admin {admin_id} ga yuborishda xato: {e}")
            
    is_admin_user = db.is_admin(user.id)
    await message.answer(
        "✅ Murojaatingiz adminga yetkazildi.", 
        reply_markup=get_admin_menu() if is_admin_user else get_user_menu()
    )
    await state.clear()


# --- 3. INLINE TUGMA BOSILGANDA ---
@dp.callback_query(F.data.startswith("reply_to_"))
async def start_reply_to_user(call: types.CallbackQuery, state: FSMContext):
    target_user_id = call.data.split("reply_to_")[1]
    
    await state.update_data(reply_target_id=target_user_id)
    await state.set_state(AdminState.waiting_for_reply)
    
    await call.message.answer(
        f"✍️ <b>ID: <code>{target_user_id}</code></b> foydalanuvchiga javobingizni yozing:",
        parse_mode="HTML",
        reply_markup=get_cancel_kb()
    )
    await call.answer()


# --- 4. STATE ORQALI JAVOB YUBORISH ---
@dp.message(AdminState.waiting_for_reply)
async def send_reply_to_user(message: types.Message, state: FSMContext):
    if message.text in (ADMIN_NAV_BUTTONS + USER_NAV_BUTTONS) or message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Javob yuborish bekor qilindi.", reply_markup=get_admin_menu())
        return

    data = await state.get_data()
    target_user_id = data.get("reply_target_id")
    
    safe_reply = html.escape(message.text)
    user_msg = (
        f"🔔 <b>Murojaatingizga admindan javob keldi:</b>\n\n"
        f"💬 {safe_reply}"
    )
    
    try:
        await bot.send_message(chat_id=int(target_user_id), text=user_msg, parse_mode="HTML")
        await message.answer("✅ Javobingiz foydalanuvchiga muvaffaqiyatli yetkazildi!", reply_markup=get_admin_menu())
    except Exception as e:
        await message.answer(f"❌ Javob yuborishda xatolik: {e}", reply_markup=get_admin_menu())
        
    await state.clear()

@dp.callback_query(F.data == "cancel_action")
async def cancel_action_handler(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Amaliyot bekor qilindi.")
    await call.answer()

@dp.message(F.text == "📊 Statistika")
async def show_statistics(message: types.Message, state: FSMContext):
    await state.clear()
    if not db.is_admin(message.from_user.id):
        return
    
    stats = db.get_stats()
    text = (
        "📊 **Qo‘qon shahar 4-son texnikumi bot statistikasi:**\n\n"
        f"👤 **Foydalanuvchilar:** {stats['users']} ta\n"
        f"📁 **Bo'limlar:** {stats['categories']} ta\n"
        f"📖 **Kitoblar/Qismlar:** {stats['books']} ta"
    )
    await message.answer(text, parse_mode="Markdown")

# --- BOSHQARUV PANELI VA ADMINLARNI BOSHQARISH ---
@dp.message(F.text == "⚙️ Boshqaruv")
async def manage_panel(message: types.Message, state: FSMContext):
    await state.clear()
    if not db.is_admin(message.from_user.id):
        return
    
    keyboard = [
        [InlineKeyboardButton(text="➕ Yangi bo'lim qo'shish", callback_data="add_new_category")],
        [InlineKeyboardButton(text="✏️ Bo'limlarni tahrirlash / o'chirish", callback_data="manage_categories_list")],
        [InlineKeyboardButton(text="👥 Adminlarni boshqarish", callback_data="manage_admins_list")]
    ]
    await message.answer("⚙️ **Boshqaruv paneli:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

@dp.callback_query(F.data == "manage_admins_list")
async def manage_admins_list(call: types.CallbackQuery):
    if call.from_user.id != SUPER_ADMIN_ID:
        await call.answer("❌ Adminlarni faqat Bosh Admin boshqara oladi!", show_alert=True)
        return
        
    admins = db.get_all_admins()
    keyboard = []
    
    for admin in admins:
        admin_id, role = admin[0], admin[1]
        btn_text = f"👤 ID: {admin_id} ({role})"
        if admin_id != SUPER_ADMIN_ID:
            keyboard.append([
                InlineKeyboardButton(text=btn_text, callback_data="ignore"),
                InlineKeyboardButton(text="❌ O'chirish", callback_data=f"del_admin_{admin_id}")
            ])
        else:
            keyboard.append([InlineKeyboardButton(text=f"👑 {btn_text}", callback_data="ignore")])
            
    keyboard.append([InlineKeyboardButton(text="➕ Yangi Admin qo'shish", callback_data="add_new_admin")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="cancel_action")])
    
    await call.message.edit_text("👥 **Tizimdagi adminlar:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "add_new_admin")
async def add_admin_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("Yangi yordamchi adminning **Telegram ID** sini kiriting (masalan: `123456789`):", parse_mode="Markdown", reply_markup=get_cancel_kb())
    await state.set_state(AdminState.waiting_for_new_admin_id)
    await call.answer()

@dp.message(AdminState.waiting_for_new_admin_id, TextNotInNav())
async def add_admin_save(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ Telegram ID faqat raqamlardan iborat bo'lishi kerak. Qayta kiriting:")
        return
        
    new_admin_id = int(text)
    db.add_admin(new_admin_id, role="admin")
    await message.answer(f"✅ `ID: {new_admin_id}` foydalanuvchisi yordamchi admin qilib tayinlandi!", parse_mode="Markdown", reply_markup=get_admin_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("del_admin_"))
async def delete_admin_call(call: types.CallbackQuery):
    if call.from_user.id != SUPER_ADMIN_ID:
        await call.answer("❌ Faqat Bosh Admin adminlarni o'chira oladi!", show_alert=True)
        return
        
    admin_id = int(call.data.split("_")[2])
    db.remove_admin(admin_id)
    await call.answer("Yordamchi admin o'chirildi!", show_alert=True)
    await manage_admins_list(call)

# --- BO'LIMLARNI BOSHQARISH ---
@dp.callback_query(F.data == "add_new_category")
async def add_category_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("Yangi bo'lim nomini kiriting:", reply_markup=get_cancel_kb())
    await state.set_state(AdminState.waiting_for_category_name)
    await call.answer()

@dp.message(AdminState.waiting_for_category_name, TextNotInNav())
async def add_category_save(message: types.Message, state: FSMContext):
    cat_name = message.text.strip()
    db.add_category(cat_name)
    await message.answer(f"✅ '{cat_name}' bo'limi yaratildi!", reply_markup=get_admin_menu())
    await state.clear()

@dp.callback_query(F.data == "manage_categories_list")
async def manage_categories_list(call: types.CallbackQuery):
    categories = db.get_categories()
    if not categories:
        await call.message.edit_text("Hozircha bo'limlar yo'q.", reply_markup=get_cancel_kb())
        return
        
    keyboard = []
    for cat in categories:
        cat_id, cat_name = cat[0], cat[1]
        keyboard.append([
            InlineKeyboardButton(text=f"📁 {cat_name}", callback_data="ignore"),
            InlineKeyboardButton(text="✏️", callback_data=f"edit_cat_{cat_id}"),
            InlineKeyboardButton(text="❌", callback_data=f"confirm_del_cat_{cat_id}")
        ])
    keyboard.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="cancel_action")])
    await call.message.edit_text("⚙️ **Bo'limni tanlang:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data.startswith("edit_cat_"))
async def edit_category_start(call: types.CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split("_")[2])
    await state.update_data(edit_cat_id=cat_id)
    await call.message.edit_text("Bo'lim uchun yangi nom kiriting:", reply_markup=get_cancel_kb())
    await state.set_state(AdminState.waiting_for_edit_cat_name)
    await call.answer()

@dp.message(AdminState.waiting_for_edit_cat_name, TextNotInNav())
async def edit_category_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db.update_category(data['edit_cat_id'], message.text.strip())
    await message.answer("✅ Bo'lim nomi yangilandi!", reply_markup=get_admin_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("confirm_del_cat_"))
async def confirm_delete_category(call: types.CallbackQuery):
    cat_id = int(call.data.split("_")[3])
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"del_cat_{cat_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="manage_categories_list")
        ]
    ]
    await call.message.edit_text("⚠️ **Haqiqatdan ham ushbu bo'limni o'chirmoqchimisiz?**", 
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data.startswith("del_cat_"))
async def delete_category_call(call: types.CallbackQuery):
    cat_id = int(call.data.split("_")[2])
    db.delete_category(cat_id)
    await call.message.edit_text("✅ Bo'lim o'chirildi!")
    await call.answer()

# --- KITOB QO'SHISH BOSQICHALARI ---
@dp.message(F.text == "📥 Kitob qo'shish")
async def add_book_start(message: types.Message, state: FSMContext):
    await state.clear()
    if not db.is_admin(message.from_user.id):
        return
    categories = db.get_categories()
    if not categories:
        await message.answer("❌ Avval kamida bitta bo'lim yarating!")
        return
    
    await message.answer("📥 Kitob faylini (PDF, Word) yuboring:", reply_markup=get_cancel_kb())
    await state.set_state(AdminState.waiting_for_book_file)

@dp.message(AdminState.waiting_for_book_file, F.document)
async def add_book_file(message: types.Message, state: FSMContext):
    try:
        sent_doc = await bot.send_document(
            chat_id=CHANNEL_ID,
            document=message.document.file_id,
            caption=f"📥 **Yangi fayl:** {message.document.file_name}"
        )
        await state.update_data(file_id=sent_doc.document.file_id)
        await message.answer("📝 Kitob nomini kiriting (masalan: *Fizika 9-sinf*):", parse_mode="Markdown", reply_markup=get_cancel_kb())
        await state.set_state(AdminState.waiting_for_book_title)
    except Exception as e:
        logging.error(f"Kanalga yuklashda xato: {e}")
        await message.answer("❌ Xatolik! Bot yopiq kanalda Admin ekanligini va CHANNEL_ID to'g'riligini tekshiring.")
        await state.clear()

@dp.message(AdminState.waiting_for_book_title, TextNotInNav())
async def add_book_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.answer("📄 Qismini kiriting (masalan: *1-qism* yoki *To'liq*):", parse_mode="Markdown", reply_markup=get_cancel_kb())
    await state.set_state(AdminState.waiting_for_part_name)

@dp.message(AdminState.waiting_for_part_name, TextNotInNav())
async def add_book_part(message: types.Message, state: FSMContext):
    await state.update_data(part_name=message.text.strip())
    
    categories = db.get_categories()
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(text=f"📁 {cat[1]}", callback_data=f"save_book_cat_{cat[0]}")])
    keyboard.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")])
        
    await message.answer("📚 Kitob qaysi bo'limga tegishli?", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await state.set_state(AdminState.waiting_for_book_category)

@dp.callback_query(AdminState.waiting_for_book_category, F.data.startswith("save_book_cat_"))
async def add_book_finish(call: types.CallbackQuery, state: FSMContext):
    category_id = int(call.data.split("_")[3])
    data = await state.get_data()
    
    db.add_book(category_id, data['title'], data['part_name'], data['file_id'])
    await call.message.edit_text(f"✅ **{data['title']}** ({data['part_name']}) kitobi arxivlandi va saqlandi!", parse_mode="Markdown")
    await state.clear()
    await call.answer()

# --- KATALOG, KO'RISH VA XAVFSIZ O'CHIRISH ---
@dp.message(F.text == "📚 Katalog")
async def show_categories(message: types.Message, state: FSMContext):
    await state.clear()
    await render_categories(message)

async def render_categories(event: types.Message | types.CallbackQuery):
    categories = db.get_categories()
    if not categories:
        msg = "Hozircha bo'limlar yo'q."
        if isinstance(event, types.CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return
    
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(text=f"📁 {cat[1]}", callback_data=f"show_cat_{cat[0]}")])
        
    inline_kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text("📚 **Bo'limni tanlang:**", reply_markup=inline_kb, parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer("📚 **Bo'limni tanlang:**", reply_markup=inline_kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("show_cat_"))
async def show_books_in_category(call: types.CallbackQuery):
    cat_id = int(call.data.split("_")[2])
    unique_books = db.get_unique_books_by_category(cat_id)
    
    keyboard = []
    if unique_books:
        for book in unique_books:
            title = book[0]
            keyboard.append([InlineKeyboardButton(text=f"📖 {title}", callback_data=f"show_parts_{cat_id}_{title}")])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_categories")])
    await call.message.edit_text("📖 **Kitobni tanlang:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data.startswith("show_parts_"))
async def show_book_parts(call: types.CallbackQuery):
    _, _, cat_id, title = call.data.split("_", 3)
    parts = db.get_parts_by_title(int(cat_id), title)
    is_adm = db.is_admin(call.from_user.id)
    
    keyboard = []
    if parts:
        for part in parts:
            book_id, part_name = part[0], part[1]
            row = [InlineKeyboardButton(text=f"📄 {part_name}", callback_data=f"get_book_{book_id}")]
            if is_adm:
                row.append(InlineKeyboardButton(text="✏️", callback_data=f"edit_book_{book_id}"))
                row.append(InlineKeyboardButton(text="❌", callback_data=f"confirm_del_book_{book_id}"))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"show_cat_{cat_id}")])
        await call.message.edit_text(f"📚 **{title}** mavjud qismlari:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
    else:
        keyboard.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"show_cat_{cat_id}")])
        await call.message.edit_text("⚠️ Ushbu kitobning barcha qismlari o'chirib bo'lindi.", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await call.answer()

# O'chirishni tasdiqlash
@dp.callback_query(F.data.startswith("confirm_del_book_"))
async def confirm_delete_book(call: types.CallbackQuery):
    book_id = int(call.data.split("_")[3])
    book = db.get_book_by_id(book_id)
    
    if not book:
        await call.answer("Kitob topilmadi!", show_alert=True)
        return
        
    cat_id, title, part_name = book[1], book[2], book[3]
    
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"del_book_{book_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"show_parts_{cat_id}_{title}")
        ]
    ]
    
    await call.message.edit_text(
        f"⚠️ **Haqiqatdan ham ushbu kitobni o'chirmoqchimisiz?**\n\n📖 Nom: **{title}**\n📄 Qism: **{part_name}**", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), 
        parse_mode="Markdown"
    )
    await call.answer()

# O'chirishni amalga oshirish
@dp.callback_query(F.data.startswith("del_book_"))
async def delete_book_call(call: types.CallbackQuery):
    book_id = int(call.data.split("_")[2])
    book = db.get_book_by_id(book_id)
    
    if book:
        cat_id = book[1]
        title = book[2]
        db.delete_book(book_id)
        await call.answer("Kitob qismi o'chirildi!", show_alert=True)
        
        parts = db.get_parts_by_title(cat_id, title)
        is_adm = db.is_admin(call.from_user.id)
        keyboard = []
        
        if parts:
            for part in parts:
                b_id, part_name = part[0], part[1]
                row = [InlineKeyboardButton(text=f"📄 {part_name}", callback_data=f"get_book_{b_id}")]
                if is_adm:
                    row.append(InlineKeyboardButton(text="✏️", callback_data=f"edit_book_{b_id}"))
                    row.append(InlineKeyboardButton(text="❌", callback_data=f"confirm_del_book_{b_id}"))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"show_cat_{cat_id}")])
            await call.message.edit_text(f"📚 **{title}** mavjud qismlari:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
        else:
            unique_books = db.get_unique_books_by_category(cat_id)
            for b in unique_books:
                keyboard.append([InlineKeyboardButton(text=f"📖 {b[0]}", callback_data=f"show_parts_{cat_id}_{b[0]}")])
            keyboard.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_categories")])
            await call.message.edit_text("📖 **Kitobni tanlang:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
    else:
        await call.answer("Kitob topilmadi!", show_alert=True)

# --- KITOBNI TAHRIRLASH VA FAYLINI ALMASHTIRISH ---
@dp.callback_query(F.data.startswith("edit_book_"))
async def edit_book_options(call: types.CallbackQuery, state: FSMContext):
    book_id = int(call.data.split("_")[2])
    book = db.get_book_by_id(book_id)
    if not book:
        await call.answer("Kitob topilmadi!", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton(text="📝 Nomi va qismini tahrirlash", callback_data=f"edit_text_{book_id}")],
        [InlineKeyboardButton(text="🔄 Kitob faylini (PDF) almashtirish", callback_data=f"change_file_{book_id}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"show_parts_{book[1]}_{book[2]}")]
    ]
    
    await call.message.edit_text(
        f"⚙️ **{book[2]}** ({book[3]}) kitobini tahrirlash:\nNimani o'zgartirmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )
    await call.answer()

@dp.callback_query(F.data.startswith("edit_text_"))
async def edit_book_text_start(call: types.CallbackQuery, state: FSMContext):
    book_id = int(call.data.split("_")[2])
    book = db.get_book_by_id(book_id)
    await state.update_data(edit_book_id=book_id, old_title=book[2], old_part=book[3])
    await call.message.edit_text(f"📝 Yangi nom kiriting (Hozirgi: *{book[2]}*):", parse_mode="Markdown", reply_markup=get_cancel_kb())
    await state.set_state(AdminState.waiting_for_edit_book_title)
    await call.answer()

@dp.message(AdminState.waiting_for_edit_book_title, TextNotInNav())
async def edit_book_title_save(message: types.Message, state: FSMContext):
    new_title = message.text.strip()
    await state.update_data(new_title=new_title)
    data = await state.get_data()
    
    await message.answer(f"📄 Qism nomini kiriting (Hozirgi: *{data['old_part']}*):", parse_mode="Markdown", reply_markup=get_cancel_kb())
    await state.set_state(AdminState.waiting_for_edit_book_part)

@dp.message(AdminState.waiting_for_edit_book_part, TextNotInNav())
async def edit_book_part_save(message: types.Message, state: FSMContext):
    new_part = message.text.strip()
    data = await state.get_data()
    
    db.update_book(data['edit_book_id'], data['new_title'], new_part)
    await message.answer(f"✅ Kitob ma'lumotlari yangilandi!\n📖 Nom: **{data['new_title']}**\n📄 Qism: **{new_part}**", reply_markup=get_admin_menu(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data.startswith("change_file_"))
async def change_file_start(call: types.CallbackQuery, state: FSMContext):
    book_id = int(call.data.split("_")[2])
    await state.update_data(replace_book_id=book_id)
    await call.message.edit_text("📥 Yangi kitob faylini (PDF/Word) yuboring:", reply_markup=get_cancel_kb())
    await state.set_state(AdminState.waiting_for_new_book_file)
    await call.answer()

@dp.message(AdminState.waiting_for_new_book_file, F.document)
async def change_file_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    book_id = data['replace_book_id']
    
    try:
        sent_doc = await bot.send_document(
            chat_id=CHANNEL_ID,
            document=message.document.file_id,
            caption=f"🔄 **Yangi almashtirilgan fayl:** {message.document.file_name}"
        )
        
        db.update_book_file(book_id, sent_doc.document.file_id)
        
        await message.answer("✅ Kitob fayli muvaffaqiyatli almashtirildi!", reply_markup=get_admin_menu())
        await state.clear()
    except Exception as e:
        logging.error(f"Fayl almashtirishda xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi. Fayl kanalga yuklanmadi.")
        await state.clear()

@dp.callback_query(F.data.startswith("get_book_"))
async def send_book(call: types.CallbackQuery):
    book_id = int(call.data.split("_")[2])
    book = db.get_book_by_id(book_id)
    if book:
        await call.message.answer_document(document=book[4], caption=f"📚 **{book[2]}** ({book[3]})", parse_mode="Markdown")
        await call.answer()

@dp.callback_query(F.data == "back_to_categories")
async def back_to_categories_handler(call: types.CallbackQuery):
    await render_categories(call)

@dp.message(F.text == "🔍 Qidirish")
async def search_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Qidirmoqchi bo'lgan kitob nomini kiriting:", reply_markup=get_cancel_kb())
    await state.set_state(AdminState.waiting_for_search_query)

@dp.message(AdminState.waiting_for_search_query, TextNotInNav())
async def search_process(message: types.Message, state: FSMContext):
    query = message.text.strip()
    results = db.search_books(query)
    
    if not results:
        await message.answer("🔍 Hech narsa topilmadi.")
    else:
        keyboard = []
        for res in results:
            keyboard.append([InlineKeyboardButton(text=f"📖 {res[1]} ({res[2]})", callback_data=f"get_book_{res[0]}")])
        await message.answer(f"🔍 **'{query}' bo'yicha natijalar:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
        
    await state.clear()

@dp.callback_query(F.data == "ignore")
async def ignore_handler(call: types.CallbackQuery):
    await call.answer()

async def main():
    logging.basicConfig(level=logging.INFO)
    await set_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    # --- USHLANMAGAN SO'ROVLARNI ZAVOD BO'YICHA QAMRAB OLISH ---

# Barcha Inline tugmalar uchun
@dp.callback_query()
async def unhandled_callback(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("⚠️ Ushbu tugma eskirgan yoki buyruq topilmadi.", show_alert=True)

# Barcha nomalum xabarlar va tugmalar uchun
@dp.message()
async def unhandled_message(message: types.Message, state: FSMContext):
    await state.clear()
    if db.is_admin(message.from_user.id):
        await message.answer("❓ Nomalum buyruq.", reply_markup=get_admin_menu())
    else:
        await message.answer("❓ Nomalum buyruq.", reply_markup=get_user_menu())
# 738-qatordan boshlab tekshiring:
async def main():
    # Funksiya ichidagi barcha qatorlar 4 ta joy (space) o'ngga surilgan bo'lishi kerak!
    threading.Thread(target=run_flask, daemon=True).start()
    
    logging.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())