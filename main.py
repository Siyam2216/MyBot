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

# মেনু বাটনসমূহ
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
        await db.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, verified INTEGER DEFAULT 0)''')
        await db.commit()

async def check_channels(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

# --- হ্যান্ডলারসমূহ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    args = message.text.split()
    if len(args) > 1: # রেফারেল লজিক
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = balance + 50 WHERE user_id = ?", (args[1],))
            await db.commit()
    await message.answer("👋 Welcome! Join both channels & click Verify:", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Channel 1", url="https://t.me/USDT_GIVEAWAY_ii")],
            [InlineKeyboardButton(text="📢 Channel 2", url="https://t.me/USDT_GIVEAWAY_iii")],
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
            await callback.message.answer("🎉 Congratulations! Received 200 Coins.", reply_markup=get_main_menu())
        else:
            await callback.answer("❌ Join both channels first!", show_alert=True)

@dp.message(F.text == "👥 Refer & Earn")
async def refer_info(message: types.Message):
    bot_name = (await bot.get_me()).username
    link = f"https://t.me/{bot_name}?start={message.from_user.id}"
    await message.answer(f"🔗 Link: {link}\n💰 Earn 50 Coins/Refer!", reply_markup=get_main_menu())
    try: # ২য় চ্যানেলে অটো পোস্ট
        await bot.send_message(chat_id="@USDT_GIVEAWAY_iii", text=f"📢 New Referral Promo! User: @{message.from_user.username or 'N/A'}\nJoin: {link}")
    except: pass

@dp.message(F.text == "🏆 Leaderboard")
async def leaderboard(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await (await db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 5")).fetchall()
    text = "🏆 Top 5 Users:\n" + "\n".join([f"{i+1}. ID {r[0]}: {r[1]} Coins" for i, r in enumerate(rows)])
    await message.answer(text, reply_markup=get_main_menu())

# --- উইথড্রল স্টেট হ্যান্ডলার ---
@dp.message(F.text == "💳 Withdraw")
async def withdraw_start(message: types.Message, state: FSMContext):
    await message.answer("Enter Amount (Min 10):", reply_markup=get_back_menu())
    await state.set_state(WithdrawState.waiting_for_amount)

@dp.message(F.text == "🔙 Back to Main Menu")
async def back_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Main Menu:", reply_markup=get_main_menu())

@dp.message(WithdrawState.waiting_for_amount)
async def p_amt(message: types.Message, state: FSMContext):
    if message.text == "🔙 Back to Main Menu": return await back_main(message, state)
    try:
        if float(message.text) < 10: raise ValueError
        await state.update_data(amount=message.text)
        await message.answer("Method (TRC20/BEP20):", reply_markup=get_back_menu())
        await state.set_state(WithdrawState.waiting_for_method)
    except: await message.answer("❌ Invalid number or < 10!")

@dp.message(WithdrawState.waiting_for_method)
async def p_met(message: types.Message, state: FSMContext):
    if message.text == "🔙 Back to Main Menu": return await back_main(message, state)
    await state.update_data(method=message.text)
    await message.answer("Address:", reply_markup=get_back_menu())
    await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def p_addr(message: types.Message, state: FSMContext):
    if message.text == "🔙 Back to Main Menu": return await back_main(message, state)
    data = await state.get_data()
    async with aiohttp.ClientSession() as s:
        await s.post(WEB_APP_URL, json={"user_id": message.from_user.id, "amount": data['amount'], "method": data['method'], "address": message.text})
    await message.answer("✅ Request submitted!", reply_markup=get_main_menu())
    await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
