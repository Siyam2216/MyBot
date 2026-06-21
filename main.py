import asyncio
import aiosqlite
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest

# Configuration
API_TOKEN = os.environ.get('API_TOKEN')
WEB_APP_URL = os.environ.get('WEB_APP_URL')
CHANNEL_1 = "@USDT_GIVEAWAY_ii"
CHANNEL_2 = "@USDT_GIVEAWAY_iii"
CHANNEL_ID = "@USDT_GIVEAWAY_iii"
DB_PATH = "/var/data/bot_data.db"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class WithdrawState(StatesGroup):
    waiting_for_method = State()
    waiting_for_address = State()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
                          (user_id INTEGER PRIMARY KEY, balance REAL, referred_by INTEGER)''')
        await db.commit()

async def check_subscription(user_id, channel):
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except TelegramBadRequest:
        return False

async def send_to_sheet(user_id, referrals, method, address):
    if not WEB_APP_URL: return
    async with aiohttp.ClientSession() as session:
        payload = {"user_id": user_id, "referrals": referrals, "method": method, "address": address}
        async with session.post(WEB_APP_URL, json=payload) as response:
            return await response.text()

def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Account"), KeyboardButton(text="👥 Refer & Earn")],
        [KeyboardButton(text="💳 Withdraw"), KeyboardButton(text="📈 Price Info")],
        [KeyboardButton(text="🏆 Leaderboard")]
    ], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 else None
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance, referred_by) VALUES (?, ?, ?)", 
                         (user_id, 0.0, referrer_id))
        await db.commit()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Join Channel 1", url="https://t.me/USDT_GIVEAWAY_ii")],
        [InlineKeyboardButton(text="Join Channel 2", url="https://t.me/USDT_GIVEAWAY_iii")],
        [InlineKeyboardButton(text="✅ Verify & Claim", callback_data="verify_join")]
    ])
    await message.answer("👋 Welcome! Join our channels to claim your bonus:", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            await message.answer(f"👤 **Account Details**\n\n🆔 **User ID:** `{message.from_user.id}`\n💰 **Balance:** {balance} Coins", parse_mode="Markdown")

@dp.message(F.text.contains("Refer & Earn"))
async def refer(message: types.Message):
    bot_info = await bot.get_me()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (message.from_user.id,)) as cursor:
            refer_count = (await cursor.fetchone())[0]
    await message.answer(f"🔥 **Boost Your Earnings!**\n\n🔗 **Link:** https://t.me/{bot_info.username}?start={message.from_user.id}\n\n👥 **Total Referrals:** {refer_count}\n💰 **Earn:** 100 Coins per referral!", parse_mode="Markdown")

@dp.message(F.text == "🏆 Leaderboard")
async def show_leaderboard(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        # Get Top 10
        cursor = await db.execute("SELECT referred_by, COUNT(*) as count FROM users WHERE referred_by IS NOT NULL GROUP BY referred_by ORDER BY count DESC LIMIT 10")
        top_rows = await cursor.fetchall()
        # Get all for ranking
        all_ranks = await db.execute("SELECT referred_by, COUNT(*) as count FROM users WHERE referred_by IS NOT NULL GROUP BY referred_by ORDER BY count DESC")
        rankings = await all_ranks.fetchall()
        
    user_rank = "Unranked"
    user_count = 0
    for i, (ref_id, count) in enumerate(rankings, 1):
        if ref_id == user_id:
            user_rank = i
            user_count = count
            break
            
    text = "🏆 **Top 10 Referrers:**\n\n" + "".join([f"{i+1}. `{r[0]}` — {r[1]} Refs\n" for i, r in enumerate(top_rows)])
    text += f"\n--------------------------\n📍 **Your Rank:** {user_rank}\n👥 **Your Refs:** {user_count}"
    await message.answer(text, parse_mode="Markdown")

# ... [Keep Withdraw and Price Info handlers from previous version] ...

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
