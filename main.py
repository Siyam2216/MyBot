import asyncio, aiosqlite, os, aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = os.environ.get('API_TOKEN')
WEB_APP_URL = os.environ.get('WEB_APP_URL')
CHANNELS = ["@USDT_GIVEAWAY_ii", "@USDT_GIVEAWAY_iii"]
DB_PATH = "bot_data.db"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ডাটাবেস ইনিশিয়ালাইজেশন
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, 
            balance REAL DEFAULT 0, 
            verified INTEGER DEFAULT 0, 
            referrals INTEGER DEFAULT 0)''')
        await db.commit()

# মেনু বাটন
def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Account"), KeyboardButton(text="👥 Refer & Earn")],
        [KeyboardButton(text="💳 Withdraw"), KeyboardButton(text="📈 Price Info")],
        [KeyboardButton(text="🏆 Leaderboard")]
    ], resize_keyboard=True)

# সব হ্যান্ডলার
@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance, referrals FROM users WHERE user_id=?", (message.from_user.id,))
        row = await cur.fetchone()
        bal, refs = row if row else (0, 0)
    await message.answer(f"👤 User ID: {message.from_user.id}\n💰 Balance: {bal} Coins\n👥 Total Referrals: {refs}", reply_markup=get_main_menu())

@dp.message(F.text == "👥 Refer & Earn")
async def refer_info(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT referrals FROM users WHERE user_id=?", (message.from_user.id,))
        row = await cur.fetchone()
        refs = row[0] if row else 0
    bot_name = (await bot.get_me()).username
    link = f"https://t.me/{bot_name}?start={message.from_user.id}"
    await message.answer(f"🔗 Link: {link}\n💰 Total Refs: {refs}", reply_markup=get_main_menu())
    try:
        await bot.send_message(chat_id="@USDT_GIVEAWAY_iii", text=f"📢 Referral Promo!\nUser ID: {message.from_user.id}\nTotal Refs: {refs}\nJoin: {link}")
    except: pass

@dp.message(F.text == "📈 Price Info")
async def price_info(message: types.Message):
    await message.answer("📈 1 Coin = 0.01 USDT\n🚀 Listing Coming Soon!", reply_markup=get_main_menu())

@dp.message(F.text == "🏆 Leaderboard")
async def leaderboard(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await (await db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 5")).fetchall()
        cur_pos = await db.execute("SELECT count(*)+1 FROM users WHERE balance > (SELECT balance FROM users WHERE user_id=?)", (message.from_user.id,))
        pos = (await cur_pos.fetchone())[0]
    text = "🏆 Top 5 Users:\n" + "\n".join([f"{i+1}. ID {r[0]}: {r[1]} Coins" for i, r in enumerate(rows)])
    await message.answer(f"{text}\n\n📍 Your Position: {pos}", reply_markup=get_main_menu())

# (অন্যান্য হ্যান্ডলার আগের মতো রাখুন)
