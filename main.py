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

def get_join_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Join Channel 1", url="https://t.me/USDT_GIVEAWAY_ii")],
        [InlineKeyboardButton(text="Join Channel 2", url="https://t.me/USDT_GIVEAWAY_iii")],
        [InlineKeyboardButton(text="✅ Verify & Claim", callback_data="verify_join")]
    ])

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
    await message.answer("👋 Welcome! Please join our channels to claim your bonus:", reply_markup=get_join_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "verify_join")
async def verify(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] >= 200:
                await callback.answer("❌ You already claimed your bonus!", show_alert=True)
                return
    if await check_subscription(user_id, CHANNEL_1) and await check_subscription(user_id, CHANNEL_2):
        await callback.message.delete()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = balance + 200 WHERE user_id = ?", (user_id,))
            await db.commit()
        await callback.message.answer("🎉 Congratulations! You received 200 coins!", reply_markup=get_main_menu(), parse_mode="Markdown")
    else:
        await callback.answer("❌ Join both channels first!", show_alert=True)

@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            await message.answer(f"👤 **Account Details**\n\n💰 **Balance:** {balance} Coins", parse_mode="Markdown")

@dp.message(F.text == "👥 Refer & Earn")
async def refer(message: types.Message):
    bot_info = await bot.get_me()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (message.from_user.id,)) as cursor:
            result = await cursor.fetchone()
            refer_count = result[0] if result else 0
    await message.answer(f"🔥 **Boost Your Earnings!**\n\n🔗 **Link:** https://t.me/{bot_info.username}?start={message.from_user.id}\n👥 **Total Referrals:** {refer_count}", parse_mode="Markdown")

@dp.message(F.text == "💳 Withdraw")
async def withdraw_start(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (message.from_user.id,))
        refer_count = (await cursor.fetchone())[0]
    if refer_count < 20:
        await message.answer(f"🚫 **Withdrawal Locked!**\nYou need 20 referrals. Current: {refer_count}/20", parse_mode="Markdown")
        return
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="USDT TRC20"), KeyboardButton(text="USDT BEP20")], [KeyboardButton(text="Binance ID")]], resize_keyboard=True)
    await message.answer("✅ **Withdrawal Open!** Select your payment method:", reply_markup=kb, resize_keyboard=True)
    await state.set_state(WithdrawState.waiting_for_method)

@dp.message(WithdrawState.waiting_for_method)
async def process_method(message: types.Message, state: FSMContext):
    await state.update_data(method=message.text)
    await message.answer(f"Enter your {message.text} address/ID:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (message.from_user.id,))
        refs = (await cursor.fetchone())[0]
    await send_to_sheet(message.from_user.id, refs, data['method'], message.text)
    await message.answer("✅ **Submitted!** Your payment request is being processed.", reply_markup=get_main_menu(), parse_mode="Markdown")
    await state.clear()

@dp.message(F.text == "📈 Price Info")
async def price(message: types.Message):
    await message.answer("📈 **Price Prediction:** 0.01 USDT to 1.00 USDT based on total volume. 🗓 Official price set on 1st July.", parse_mode="Markdown")

@dp.message(F.text == "🏆 Leaderboard")
async def show_leaderboard(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT referred_by, COUNT(*) as count FROM users WHERE referred_by IS NOT NULL GROUP BY referred_by ORDER BY count DESC LIMIT 10")
        rows = await cursor.fetchall()
    text = "🏆 **Top 10 Referrers:**\n\n" + "".join([f"{i+1}. User `{r[0]}` — {r[1]} Refs\n" for i, r in enumerate(rows)])
    await message.answer(text, parse_mode="Markdown")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
