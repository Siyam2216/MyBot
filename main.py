import asyncio
import aiosqlite
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

# --- Utility Functions ---
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Account", callback_data="menu_account"), 
         InlineKeyboardButton(text="👥 Refer & Earn", callback_data="menu_refer")],
        [InlineKeyboardButton(text="💳 Withdraw", callback_data="menu_withdraw"), 
         InlineKeyboardButton(text="📈 Price Info", callback_data="menu_price")],
        [InlineKeyboardButton(text="🏆 Leaderboard", callback_data="menu_leaderboard")]
    ])

async def send_to_sheet(user_id, referrals, method, address):
    if not WEB_APP_URL: return
    async with aiohttp.ClientSession() as session:
        payload = {"user_id": user_id, "referrals": referrals, "method": method, "address": address}
        async with session.post(WEB_APP_URL, json=payload) as response:
            return await response.text()

# --- Handlers ---
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
        [InlineKeyboardButton(text="Join Channels", url="https://t.me/USDT_GIVEAWAY_ii")],
        [InlineKeyboardButton(text="✅ Verify & Claim", callback_data="verify_join")]
    ])
    await message.answer("👋 **Welcome!** Join channels and click Verify.", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "verify_join")
async def verify(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + 200 WHERE user_id = ?", (user_id,))
        await db.commit()
    await callback.message.edit_text("🎉 **Claimed 200 Coins!** Use menu below:", reply_markup=get_main_menu())

@dp.callback_query(F.data.startswith("menu_"))
async def handle_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if callback.data == "menu_account":
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
            row = await cursor.fetchone()
            await callback.message.answer(f"👤 **ID:** `{user_id}`\n💰 **Balance:** {row[0]} Coins", parse_mode="Markdown")
            
    elif callback.data == "menu_refer":
        bot_info = await bot.get_me()
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
            count = (await cursor.fetchone())[0]
        await callback.message.answer(f"🔗 **Link:** https://t.me/{bot_info.username}?start={user_id}\n👥 **Refs:** {count}", parse_mode="Markdown")
        
    elif callback.data == "menu_withdraw":
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
            refs = (await cursor.fetchone())[0]
        if refs < 20:
            await callback.answer("🚫 Need 20 referrals!", show_alert=True)
        else:
            await callback.message.answer("Choose Method:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="USDT TRC20", callback_data="meth_TRC20")],
                [InlineKeyboardButton(text="USDT BEP20", callback_data="meth_BEP20")]
            ]))
            await state.set_state(WithdrawState.waiting_for_method)

    elif callback.data == "menu_price":
        await callback.message.answer("📈 Price: 0.01 USDT - 1.00 USDT.")
        
    elif callback.data == "menu_leaderboard":
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT referred_by, COUNT(*) as count FROM users GROUP BY referred_by ORDER BY count DESC LIMIT 10")
            rows = await cursor.fetchall()
            text = "\n".join([f"{i+1}. `{r[0]}` - {r[1]} Refs" for i, r in enumerate(rows)])
            await callback.message.answer(f"🏆 **Top Referrers:**\n{text}", parse_mode="Markdown")
    
    await callback.answer()

# State handling remains similar...
@dp.callback_query(F.data.startswith("meth_"), WithdrawState.waiting_for_method)
async def process_method(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(method=callback.data.split("_")[1])
    await callback.message.answer("Enter your Address:")
    await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    # Sheet logic call here
    await message.answer("✅ Submitted!")
    await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
