import asyncio, aiosqlite, os, aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

# এনভায়রনমেন্ট ভেরিয়েবল লোড হচ্ছে
API_TOKEN = os.environ.get('API_TOKEN')
WEB_APP_URL = os.environ.get('WEB_APP_URL')
CHANNELS = ["@USDT_GIVEAWAY_ii", "@USDT_GIVEAWAY_iii"]
DB_PATH = "bot_data.db"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class WithdrawState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_method = State()
    waiting_for_address = State()

def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Account"), KeyboardButton(text="👥 Refer & Earn")],
        [KeyboardButton(text="💳 Withdraw"), KeyboardButton(text="📈 Price Info")],
        [KeyboardButton(text="🏆 Leaderboard")]
    ], resize_keyboard=True)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, 
            balance REAL DEFAULT 0, 
            verified INTEGER DEFAULT 0, 
            referrals INTEGER DEFAULT 0)''')
        await db.commit()

@dp.message(Command("start"))
async def start(message: types.Message):
    args = message.text.split()
    if len(args) > 1:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = balance + 50, referrals = referrals + 1 WHERE user_id = ?", (args[1],))
            await db.commit()
    
    await message.answer("👋 Welcome! Join both channels and click Verify:", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Channel 1", url="https://t.me/USDT_GIVEAWAY_ii")],
            [InlineKeyboardButton(text="📢 Channel 2", url="https://t.me/USDT_GIVEAWAY_iii")],
            [InlineKeyboardButton(text="✅ Verify Join", callback_data="verify")]
        ]))

@dp.callback_query(F.data == "verify")
async def verify(callback: types.CallbackQuery):
    try:
        # চ্যানেল চেক (সিম্পল ট্রাই-এক্সসেপ্ট)
        user_id = callback.from_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT verified FROM users WHERE user_id=?", (user_id,))
            res = await cur.fetchone()
            if res and res[0] == 1:
                return await callback.answer("⚠️ Already claimed!", show_alert=True)
            
            await db.execute("INSERT OR REPLACE INTO users (user_id, balance, verified) VALUES (?, 200, 1)", (user_id, 200))
            await db.commit()
            await callback.message.answer("🎉 Congratulations! Received 200 Coins.", reply_markup=get_main_menu())
    except Exception as e:
        await callback.answer("❌ Error occurred!")
        print(f"Verify Error: {e}")

@dp.message(F.text == "👥 Refer & Earn")
async def refer_info(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT referrals FROM users WHERE user_id=?", (message.from_user.id,))
        row = await cur.fetchone()
        refs = row[0] if row else 0
    bot_name = (await bot.get_me()).username
    link = f"https://t.me/{bot_name}?start={message.from_user.id}"
    await message.answer(f"🔗 Link: {link}\n💰 Total Referrals: {refs}", reply_markup=get_main_menu())
    try:
        await bot.send_message(chat_id="@USDT_GIVEAWAY_iii", text=f"📢 Referral Promo!\nID: {message.from_user.id}\nTotal Refs: {refs}\nJoin: {link}")
    except: pass

# (বাকি বাটনগুলো যেমন Account, Leaderboard আগের মতো রাখুন)

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
