import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# আপনার নতুন টোকেন
API_TOKEN = '8669911640:AAEZna8iEkxaRo0GWPclYw2DgJOCTC58UgI'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO)

# ডাটাবেজ কানেকশন (Async)
async def init_db():
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
                          (user_id INTEGER PRIMARY KEY, balance INTEGER, referrer_id INTEGER, verified INTEGER)''')
        await db.commit()

# মেনু ডিজাইন
def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Account"), KeyboardButton(text="👥 Refer & Earn")],
        [KeyboardButton(text="💳 Withdraw"), KeyboardButton(text="🎁 Extra Earning")],
        [KeyboardButton(text="📈 Price Info")]
    ], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT verified FROM users WHERE user_id=?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            
            if not user:
                ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
                await db.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user_id, 0, ref, 0))
                await db.commit()
                user = (0,)

            if user[0] == 1:
                await message.answer("👋 Welcome back!", reply_markup=get_main_menu())
            else:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 Join Channel 1", url="https://t.me/USDT_GIVEAWAY_ii")],
                    [InlineKeyboardButton(text="📢 Join Channel 2", url="https://t.me/USDT_GIVEAWAY_iii")],
                    [InlineKeyboardButton(text="✅ Verify & Claim", callback_data="verify")]
                ])
                await message.answer("👋 Join channels to claim 200 Coin bonus!", reply_markup=markup)

@dp.callback_query(F.data == "verify")
async def verify(call: types.CallbackQuery):
    await call.answer("✅ Checking membership...", show_alert=True)
    # এখানে আপনার মেম্বারশিপ চেক করার লজিক বসাবেন

@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            await message.reply(f"💰 Current Balance: {balance} Coin")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
