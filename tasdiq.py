import asyncio
import sqlite3
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# 1. SOZLAMALAR
TOKEN = "8211633596:AAF5J4JBEXcEyWfYPWAE0ct9hDVOpAvN1QM"
PASSWORD = "5555"  # Hisobotni ko'rish va tozalash uchun parol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. BAZA BILAN ISHLASH (Vaqt ustuni qo'shildi)
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('task_manager.db')
        self.create_table()

    def create_table(self):
        with self.conn:
            # voted_at - tasdiqlash vaqtini saqlash uchun
            self.conn.execute('''CREATE TABLE IF NOT EXISTS activity 
                   (post_id INTEGER, user_id INTEGER, user_name TEXT, link TEXT, voted_at TEXT,
                   UNIQUE(post_id, user_id))''')

    def add_vote(self, post_id, user_id, user_name, link, voted_at):
        try:
            with self.conn:
                self.conn.execute("INSERT INTO activity VALUES (?, ?, ?, ?, ?)", 
                                (post_id, user_id, user_name, link, voted_at))
            return True
        except sqlite3.IntegrityError:
            return False

    def clear_all(self):
        with self.conn:
            self.conn.execute("DELETE FROM activity")

db = Database()
bot = Bot(token=TOKEN)
dp = Dispatcher()

# 3. ADMINLIKNI TEKSHIRISH
async def is_admin(message: types.Message):
    if message.chat.type in ["group", "supergroup"]:
        member = await message.chat.get_member(message.from_user.id)
        return member.status in ["administrator", "creator"]
    return False

# 4. TUGMA
def get_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Tasdiqlash ✅", callback_data="btn_confirm")]
    ])

# 5. ADMIN POSTINI "QAYTA TUG'ILISHI"
@dp.message(F.chat.type.in_({"group", "supergroup"}), ~F.text.startswith("/"))
async def handle_admin_post(message: types.Message):
    if not message.from_user.is_bot and await is_admin(message):
        try:
            new_msg = await message.send_copy(
                chat_id=message.chat.id,
                reply_markup=get_kb()
            )
            await message.delete()
            logger.info(f"Yangi post yaratildi. ID: {new_msg.message_id}")
        except Exception as e:
            logger.error(f"Xatolik: {e}")

# 6. TUGMA BOSILISHINI QAYD ETISH (Vaqt bilan)
@dp.callback_query(F.data == "btn_confirm")
async def on_confirm(callback: types.CallbackQuery):
    post_id = callback.message.message_id
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name
    voted_at = datetime.now().strftime("%d.%m.%Y %H:%M") # Aniq vaqt
    
    chat_id_str = str(callback.message.chat.id).replace("-100", "")
    link = f"https://t.me/c/{chat_id_str}/{post_id}"
    if callback.message.chat.username:
        link = f"https://t.me/{callback.message.chat.username}/{post_id}"

    if db.add_vote(post_id, user_id, user_name, link, voted_at):
        await callback.answer(f"Tasdiqlandi! ✅ ({voted_at})")
    else:
        await callback.answer("Siz allaqachon tasdiqlagansiz! ⚠️", show_alert=True)

# 7. SHAXSIY XABARLAR (Parol nazorati va Hisobot)
@dp.message(F.chat.type == "private")
async def private_commands(message: types.Message):
    # Bazani tozalash buyrug'i
    if message.text == PASSWORD + " clear":
        db.clear_all()
        await message.answer("🗑 **Barcha hisobotlar o'chirib tashlandi!**")
        return

    # Hisobotni ko'rish
    if message.text == PASSWORD:
        conn = sqlite3.connect('task_manager.db')
        cur = conn.cursor()
        # Har bir post ostida kimlar qachon bosganini ro'yxat qilish
        cur.execute("SELECT link, GROUP_CONCAT(user_name || ' [' || voted_at || ']', '\n') FROM activity GROUP BY link")
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return await message.answer("📊 Hozircha hisobotlar bo'sh.")

        text = "📋 **Tasdiqlashlar hisoboti:**\n\n"
        for link, users in rows:
            text += f"🔗 [Postga o'tish]({link})\n👤 **Kimlar:**\n{users}\n"
            text += "----------------------------\n"
        
        if len(text) > 4096:
            for x in range(0, len(text), 4096):
                await message.answer(text[x:x+4096], disable_web_page_preview=True)
        else:
            await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)
    
    # Parol noto'g'ri bo'lsa
    else:
        await message.answer("🔑 **Kirish cheklangan.**\nIltimos, hisobotni ko'rish uchun parolni kiriting:")

async def main():
    print("Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
