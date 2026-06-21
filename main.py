import asyncio, aiosqlite, os, aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

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

# মেনু বাটন
def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Account"), KeyboardButton(text="👥 Refer & Earn")],
        [KeyboardButton(text="💳 Withdraw"), KeyboardButton(text="📈 Price Info")],
        [KeyboardButton(text="🏆 Leaderboard")]
    ], resize_keyboard=True)

def get_back_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Back to Main Menu")]], resize_keyboard=True)

# হ্যান্ডলারসমূহ
@dp.message(F.text == "💳 Withdraw")
async def withdraw_start(message: types.Message, state: FSMContext):
    await message.answer("Enter Amount (Min 10):", reply_markup=get_back_menu())
    await state.set_state(WithdrawState.waiting_for_amount)

@dp.message(F.text == "📈 Price Info")
async def price_info(message: types.Message):
    await message.answer("📈 1 Coin = 0.01 USDT\n🚀 Listing Coming Soon!", reply_markup=get_main_menu())

@dp.message(F.text == "🏆 Leaderboard")
async def leaderboard(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await (await db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 5")).fetchall()
    text = "🏆 Top 5 Users:\n" + "\n".join([f"{i+1}. ID {r[0]}: {r[1]} Coins" for i, r in enumerate(rows)])
    await message.answer(text, reply_markup=get_main_menu())

@dp.message(F.text == "🔙 Back to Main Menu")
async def back_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Main Menu:", reply_markup=get_main_menu())

# উইথড্র স্টেট হ্যান্ডলারস
@dp.message(WithdrawState.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    if message.text == "🔙 Back to Main Menu": return await back_main(message, state)
    try:
        if float(message.text) < 10: raise ValueError
        await state.update_data(amount=message.text)
        await message.answer("Method (TRC20/BEP20):", reply_markup=get_back_menu())
        await state.set_state(WithdrawState.waiting_for_method)
    except: await message.answer("❌ Invalid amount (Min 10)!")

@dp.message(WithdrawState.waiting_for_method)
async def process_method(message: types.Message, state: FSMContext):
    if message.text == "🔙 Back to Main Menu": return await back_main(message, state)
    await state.update_data(method=message.text)
    await message.answer("Address:", reply_markup=get_back_menu())
    await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    if message.text == "🔙 Back to Main Menu": return await back_main(message, state)
    data = await state.get_data()
    async with aiohttp.ClientSession() as s:
        await s.post(WEB_APP_URL, json={"user_id": message.from_user.id, "amount": data['amount'], "method": data['method'], "address": message.text})
    await message.answer("✅ Request submitted!", reply_markup=get_main_menu())
    await state.clear()

# বট স্টার্ট করার ফাংশন
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
