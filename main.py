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

# --- Functions ---
def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Account"), KeyboardButton(text="👥 Refer & Earn")],
        [KeyboardButton(text="💳 Withdraw"), KeyboardButton(text="📈 Price Info")],
        [KeyboardButton(text="🏆 Leaderboard")]
    ], resize_keyboard=True)

def get_back_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Back to Main Menu")]], resize_keyboard=True)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
                          (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, verified INTEGER DEFAULT 0)''')
        await db.commit()

async def check_channels(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

# --- Handlers ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 Welcome! Please join both channels to get 200 Coins:", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Channel 1", url="https://t.me/USDT_GIVEAWAY_ii")],
            [InlineKeyboardButton(text="📢 Join Channel 2", url="https://t.me/USDT_GIVEAWAY_iii")],
            [InlineKeyboardButton(text="✅ Verify Join", callback_data="verify")]
        ]))

@dp.callback_query(F.data == "verify")
async def verify(callback: types.CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT verified FROM users WHERE user_id=?", (callback.from_user.id,))
        res = await cur.fetchone()
        if res and res[0] == 1:
            return await callback.answer("⚠️ Already claimed!", show_alert=True)
        if await check_channels(callback.from_user.id):
            await db.execute("INSERT OR REPLACE INTO users (user_id, balance, verified) VALUES (?, 200, 1)", (callback.from_user.id,))
            await db.commit()
            await callback.message.answer("🎉 Congratulations! You received 200 Coins.", reply_markup=get_main_menu())
        else:
            await callback.answer("❌ Join both channels first!", show_alert=True)

@dp.message(F.text == "🔙 Back to Main Menu")
async def back_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Main Menu:", reply_markup=get_main_menu())

@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
        res = await cur.fetchone()
        bal = res[0] if res else 0
    await message.answer(f"💰 Balance: {bal} Coins", reply_markup=get_main_menu())

@dp.message(F.text == "💳 Withdraw")
async def withdraw_start(message: types.Message, state: FSMContext):
    await message.answer("Enter amount (Min 10):", reply_markup=get_back_menu())
    await state.set_state(WithdrawState.waiting_for_amount)

@dp.message(WithdrawState.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount < 10: return await message.answer("❌ Min 10 Coins!")
        await state.update_data(amount=amount)
        await message.answer("Enter Method (TRC20/BEP20):", reply_markup=get_back_menu())
        await state.set_state(WithdrawState.waiting_for_method)
    except: await message.answer("❌ Invalid number!")

@dp.message(WithdrawState.waiting_for_method)
async def process_method(message: types.Message, state: FSMContext):
    await state.update_data(method=message.text)
    await message.answer("Enter Address:", reply_markup=get_back_menu())
    await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    payload = {"user_id": str(message.from_user.id), "username": str(message.from_user.username), "amount": str(data['amount']), "method": str(data['method']), "address": str(message.text)}
    async with aiohttp.ClientSession() as session:
        await session.post(WEB_APP_URL, json=payload)
    await message.answer("✅ Request submitted!", reply_markup=get_main_menu())
    await state.clear()

async def main():
    await init_db()
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
