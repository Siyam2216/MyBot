import asyncio, aiosqlite, os, aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = os.environ.get('API_TOKEN')
WEB_APP_URL = os.environ.get('WEB_APP_URL')
DB_PATH = "bot_data.db" 

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class WithdrawState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_method = State()
    waiting_for_address = State()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, referred_by INTEGER)''')
        await db.commit()

async def send_to_sheet(user_id, username, amount, referrals, method, address):
    if not WEB_APP_URL: return
    try:
        async with aiohttp.ClientSession() as session:
            params = {"user_id": user_id, "username": username, "amount": amount, "referrals": referrals, "method": method, "address": address}
            async with session.post(WEB_APP_URL, params=params) as response:
                return await response.text()
    except Exception as e:
        print(f"Error: {e}")

def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="👤 Account"), KeyboardButton(text="👥 Refer & Earn")], [KeyboardButton(text="💳 Withdraw"), KeyboardButton(text="📈 Price Info")], [KeyboardButton(text="🏆 Leaderboard")]], resize_keyboard=True)

def get_back_button():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Back to Main Menu")]], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance, referred_by) VALUES (?, ?, ?)", (message.from_user.id, 0.0, None))
        await db.commit()
    await message.answer("👋 Welcome!", reply_markup=get_main_menu())

@dp.message(F.text == "🔙 Back to Main Menu")
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Main Menu:", reply_markup=get_main_menu())

@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
        res = await cur.fetchone()
        bal = res[0] if res else 0
    await message.answer(f"👤 Account Details\n🆔 ID: {message.from_user.id}\n💰 Balance: {bal} Coins", reply_markup=get_back_button())

@dp.message(F.text == "🏆 Leaderboard")
async def leaderboard(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC")
        rows = await cur.fetchall()
    user_rank = next((i+1 for i, r in enumerate(rows) if r[0] == message.from_user.id), "Unranked")
    text = "🏆 Top 5 Users:\n" + "\n".join([f"{i+1}. ID: {r[0]} - {r[1]} Coins" for i, r in enumerate(rows[:5])])
    text += f"\n\n📍 Your Rank: {user_rank}"
    await message.answer(text, reply_markup=get_back_button())

@dp.message(F.text == "💳 Withdraw")
async def withdraw_start(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        bal = (await (await db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))).fetchone())[0]
    if bal < 10: await message.answer(f"❌ Min 10 Coins needed! Balance: {bal}")
    else: 
        await message.answer(f"✅ Balance: {bal}\nEnter amount (Min 10):", reply_markup=get_back_button())
        await state.set_state(WithdrawState.waiting_for_amount)

@dp.message(WithdrawState.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    if message.text == "🔙 Back to Main Menu": return await back_to_menu(message, state)
    try:
        amount = float(message.text)
        if amount < 10: return await message.answer("❌ Min 10 Coins!")
        async with aiosqlite.connect(DB_PATH) as db:
            if amount > (await (await db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))).fetchone())[0]: return await message.answer("❌ Insufficient balance!")
        await state.update_data(amount=amount)
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="USDT TRC20"), KeyboardButton(text="USDT BEP20")], [KeyboardButton(text="🔙 Back to Main Menu")]], resize_keyboard=True)
        await message.answer("Select payment method:", reply_markup=kb)
        await state.set_state(WithdrawState.waiting_for_method)
    except: await message.answer("❌ Invalid number!")

@dp.message(WithdrawState.waiting_for_method)
async def process_method(message: types.Message, state: FSMContext):
    if message.text == "🔙 Back to Main Menu": return await back_to_menu(message, state)
    await state.update_data(method=message.text)
    await message.answer("Enter Address/ID:", reply_markup=get_back_button())
    await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    if message.text == "🔙 Back to Main Menu": return await back_to_menu(message, state)
    await state.update_data(address=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Confirm", callback_data="confirm")], [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]])
    await message.answer(f"⚠️ Confirm address:\n{message.text}", reply_markup=kb)

@dp.callback_query(F.data.in_(["confirm", "cancel"]))
async def handle_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "confirm":
        data = await state.get_data()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (data['amount'], callback.from_user.id))
            await db.commit()
        await send_to_sheet(callback.from_user.id, callback.from_user.username or "None", data['amount'], 0, data['method'], data['address'])
        await callback.message.edit_text("✅ Submitted!")
        await callback.message.answer("🏠 Main Menu:", reply_markup=get_main_menu())
    else: await callback.message.edit_text("🚫 Cancelled."); await callback.message.answer("🏠 Main Menu:", reply_markup=get_main_menu())
    await state.clear()

async def main(): await init_db(); await dp.start_polling(bot)
if __name__ == '__main__': asyncio.run(main())
