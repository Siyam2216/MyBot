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

# FSM States
class WithdrawState(StatesGroup):
    waiting_for_method = State()
    waiting_for_address = State()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
                          (user_id INTEGER PRIMARY KEY, balance REAL, referred_by INTEGER)''')
        await db.commit()

async def send_to_sheet(user_id, referrals, method, address):
    async with aiohttp.ClientSession() as session:
        payload = {"user_id": user_id, "referrals": referrals, "method": method, "address": address}
        async with session.post(WEB_APP_URL, json=payload) as response:
            return await response.text()

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance, referred_by) VALUES (?, ?, ?)", 
                         (user_id, 0.0, None))
        await db.commit()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Join Channels", url="https://t.me/USDT_GIVEAWAY_ii")],
        [InlineKeyboardButton(text="✅ Verify", callback_data="verify_join")]
    ])
    await message.answer("👋 Welcome! Join channels and click Verify.", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "💳 Withdraw")
async def withdraw_start(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (message.from_user.id,))
        refer_count = (await cursor.fetchone())[0]
    
    if refer_count < 20:
        await message.answer(f"🚫 Withdrawal Locked!\nProgress: {refer_count}/20", parse_mode="Markdown")
        return

    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="USDT TRC20"), KeyboardButton(text="USDT BEP20")],
        [KeyboardButton(text="Binance ID")]
    ], resize_keyboard=True)
    await message.answer("✅ Withdrawal Open! Select your payment method:", reply_markup=kb, parse_mode="Markdown")
    await state.set_state(WithdrawState.waiting_for_method)

@dp.message(WithdrawState.waiting_for_method)
async def process_method(message: types.Message, state: FSMContext):
    await state.update_data(method=message.text)
    await message.answer(f"Enter your {message.text} address/ID:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    method = data['method']
    address = message.text
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        refs = (await cursor.fetchone())[0]
    
    await send_to_sheet(user_id, refs, method, address)
    await message.answer("✅ Submitted! Your payment request is now processing.", reply_markup=get_main_menu(), parse_mode="Markdown")
    await state.clear()

# Add your existing Menu, Leaderboard, and Verify handlers here...

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
