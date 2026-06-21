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

async def send_to_sheet(user_id, username, referrals, method, address):
    if not WEB_APP_URL: return
    async with aiohttp.ClientSession() as session:
        payload = {"user_id": user_id, "username": username, "referrals": referrals, "method": method, "address": address}
        async with session.post(WEB_APP_URL, json=payload) as response:
            return await response.text()

def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Account"), KeyboardButton(text="👥 Refer & Earn")],
        [KeyboardButton(text="💳 Withdraw"), KeyboardButton(text="📈 Price Info")],
        [KeyboardButton(text="🏆 Leaderboard")]
    ], resize_keyboard=True)

def get_back_button():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Back to Main Menu")]], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance, referred_by) VALUES (?, ?, ?)", 
                         (message.from_user.id, 0.0, None))
        await db.commit()
    await message.answer("👋 Welcome! Use the menu below:", reply_markup=get_main_menu())

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
        await message.answer(f"👤 **Account Details**\n🆔 ID: `{message.from_user.id}`\n💰 Balance: {bal} Coins", parse_mode="Markdown", reply_markup=get_back_button())

@dp.message(F.text == "👥 Refer & Earn")
async def refer(message: types.Message):
    bot_info = await bot.get_me()
    await message.answer(f"🔗 **Referral Link:** `https://t.me/{bot_info.username}?start={message.from_user.id}`\n💰 Earn 100 coins per refer!", parse_mode="Markdown", reply_markup=get_back_button())

@dp.message(F.text == "📈 Price Info")
async def price(message: types.Message):
    await message.answer("📈 **Price Info:** 0.01 USDT - 1.00 USDT. Listing date: July 1st.", reply_markup=get_back_button())

@dp.message(F.text == "🏆 Leaderboard")
async def leaderboard(message: types.Message):
    await message.answer("🏆 **Leaderboard:** [Coming Soon]", reply_markup=get_back_button())

@dp.message(F.text == "💳 Withdraw")
async def withdraw_start(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="USDT TRC20"), KeyboardButton(text="USDT BEP20")], 
        [KeyboardButton(text="Binance ID")],
        [KeyboardButton(text="🔙 Back to Main Menu")]
    ], resize_keyboard=True)
    await message.answer("✅ Select payment method:", reply_markup=kb)
    await state.set_state(WithdrawState.waiting_for_method)

@dp.message(WithdrawState.waiting_for_method)
async def process_method(message: types.Message, state: FSMContext):
    if message.text == "🔙 Back to Main Menu": return await back_to_menu(message, state)
    await state.update_data(method=message.text)
    await message.answer("Enter your Address/ID:", reply_markup=get_back_button())
    await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    if message.text == "🔙 Back to Main Menu": return await back_to_menu(message, state)
    await state.update_data(address=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes, Confirm", callback_data="confirm_withdraw")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_withdraw")]
    ])
    await message.answer(f"⚠️ Confirm address:\n`{message.text}`", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.in_(["confirm_withdraw", "cancel_withdraw"]))
async def handle_confirmation(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "confirm_withdraw":
        data = await state.get_data()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = balance - 1000 WHERE user_id = ?", (callback.from_user.id,))
            await db.commit()
        await send_to_sheet(callback.from_user.id, callback.from_user.username, 0, data['method'], data['address'])
        await callback.message.edit_text("✅ Submitted! Waiting for approval.")
        await callback.message.answer("🏠 Main Menu:", reply_markup=get_main_menu())
    else:
        await callback.message.edit_text("🚫 Cancelled.")
        await callback.message.answer("🏠 Main Menu:", reply_markup=get_main_menu())
    await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
