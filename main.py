import asyncio, aiosqlite, os, aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

API_TOKEN = os.environ.get('API_TOKEN')
WEB_APP_URL = os.environ.get('WEB_APP_URL')
DB_PATH = "bot_data.db"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class WithdrawState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_method = State()
    waiting_for_address = State()

def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Account"), KeyboardButton(text="💳 Withdraw")],
        [KeyboardButton(text="🏆 Leaderboard")]
    ], resize_keyboard=True)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 100)''')
        await db.commit()

async def send_to_sheet(user_id, username, amount, method, address):
    if not WEB_APP_URL: return
    payload = {"user_id": str(user_id), "username": str(username), "amount": str(amount), "method": str(method), "address": str(address)}
    async with aiohttp.ClientSession() as session:
        async with session.post(WEB_APP_URL, json=payload) as response:
            return await response.text()

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)", (message.from_user.id, 100.0))
        await db.commit()
    await message.answer("👋 Welcome! Main Menu:", reply_markup=get_main_menu())

@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
        res = await cur.fetchone()
        bal = res[0] if res else 0
    await message.answer(f"💰 Balance: {bal} Coins", reply_markup=get_main_menu())

@dp.message(F.text == "💳 Withdraw")
async def withdraw_start(message: types.Message, state: FSMContext):
    await message.answer("Enter amount (Min 10):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(WithdrawState.waiting_for_amount)

@dp.message(WithdrawState.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount < 10: return await message.answer("❌ Min 10 Coins required!")
        await state.update_data(amount=amount)
        await message.answer("Enter Method (TRC20/BEP20):")
        await state.set_state(WithdrawState.waiting_for_method)
    except: await message.answer("❌ Invalid number!")

@dp.message(WithdrawState.waiting_for_method)
async def process_method(message: types.Message, state: FSMContext):
    await state.update_data(method=message.text)
    await message.answer("Enter Address:")
    await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await send_to_sheet(message.from_user.id, message.from_user.username or "None", data['amount'], data['method'], message.text)
    await message.answer("✅ Request submitted!", reply_markup=get_main_menu())
    await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
