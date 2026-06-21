import asyncio
import aiosqlite
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest

# Configuration
API_TOKEN = os.environ.get('API_TOKEN')
WEB_APP_URL = os.environ.get('WEB_APP_URL')
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
    await message.answer("👋 **Welcome!** Please join our channels and click Verify:", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "verify_join")
async def verify(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row and row[0] >= 200:
            await callback.answer("❌ You have already claimed your bonus!", show_alert=True)
            return
        await db.execute("UPDATE users SET balance = balance + 200 WHERE user_id = ?", (user_id,))
        await db.commit()
    await callback.message.delete()
    await callback.message.answer("🎉 **Claimed 200 Coins!** Use the menu below:", reply_markup=get_main_menu())

@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
        bal = (await cur.fetchone())[0]
        await message.answer(f"👤 **Account Details**\n🆔 ID: `{message.from_user.id}`\n💰 Balance: {bal} Coins", parse_mode="Markdown")

@dp.message(F.text == "👥 Refer & Earn")
async def refer(message: types.Message):
    bot_info = await bot.get_me()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (message.from_user.id,))
        cnt = (await cur.fetchone())[0]
    await message.answer(f"🔗 **Referral Link:** `https://t.me/{bot_info.username}?start={message.from_user.id}`\n👥 Total Refs: {cnt}\n💰 Earn 100 coins per refer!", parse_mode="Markdown")

@dp.message(F.text == "💳 Withdraw")
async def withdraw_start(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (message.from_user.id,))
        refs = (await cur.fetchone())[0]
    if refs < 20:
        await message.answer(f"🚫 Withdrawal Locked! Need 20 refs. Current: {refs}")
    else:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="USDT TRC20"), KeyboardButton(text="USDT BEP20")], [KeyboardButton(text="Binance ID")]], resize_keyboard=True)
        await message.answer("✅ **Select your payment method:**", reply_markup=kb)
        await state.set_state(WithdrawState.waiting_for_method)

@dp.message(WithdrawState.waiting_for_method)
async def process_method(message: types.Message, state: FSMContext):
    await state.update_data(method=message.text)
    await message.answer("Enter your Address/ID:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (message.from_user.id,))
        refs = (await cur.fetchone())[0]
    await send_to_sheet(message.from_user.id, refs, data['method'], message.text)
    await message.answer("✅ **Submitted!** Your payment request is being processed.", reply_markup=get_main_menu())
    await state.clear()

@dp.message(F.text == "📈 Price Info")
async def price(message: types.Message):
    await message.answer("📈 **Price Info:** 0.01 USDT - 1.00 USDT. Listing date: July 1st.")

@dp.message(F.text == "🏆 Leaderboard")
async def show_leaderboard(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT referred_by, COUNT(*) as count FROM users WHERE referred_by IS NOT NULL GROUP BY referred_by ORDER BY count DESC LIMIT 10")
        rows = await cur.fetchall()
        all_r = await db.execute("SELECT referred_by, COUNT(*) as count FROM users WHERE referred_by IS NOT NULL GROUP BY referred_by ORDER BY count DESC")
        ranks = await all_r.fetchall()
    
    my_rank = next((i+1 for i, (ref_id, _) in enumerate(ranks) if ref_id == message.from_user.id), "Unranked")
    my_cnt = next((count for ref_id, count in ranks if ref_id == message.from_user.id), 0)
    
    text = "🏆 **Top 10 Referrers:**\n" + "\n".join([f"{i+1}. `{r[0]}` - {r[1]} Refs" for i, r in enumerate(rows)])
    text += f"\n\n📍 Your Rank: {my_rank}\n👥 Your Refs: {my_cnt}"
    await message.answer(text, parse_mode="Markdown")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
