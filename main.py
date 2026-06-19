import asyncio
import logging
import aiosqlite
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Render-এর এনভায়রনমেন্ট থেকে টোকেনটি রিড করবে
API_TOKEN = os.environ.get('API_TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

async def init_db():
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
                          (user_id INTEGER PRIMARY KEY, balance INTEGER, referrer_id INTEGER, verified INTEGER)''')
        await db.commit()

def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Account"), KeyboardButton(text="👥 Refer & Earn")],
        [KeyboardButton(text="💳 Withdraw"), KeyboardButton(text="🎁 Extra Earning")],
        [KeyboardButton(text="📈 Price Info")]
    ], resize_keyboard=True)

# Start Command Handler
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT verified FROM users WHERE user_id=?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await db.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user_id, 0, None, 0))
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

# Button Handlers
@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            await message.answer(f"💰 Current Balance: {balance} Coin")

@dp.message(F.text == "👥 Refer & Earn")
async def refer(message: types.Message):
    await message.answer(f"🔗 Your referral link: https://t.me/your_bot_username?start={message.from_user.id}")

@dp.message(F.text == "💳 Withdraw")
async def withdraw(message: types.Message):
    await message.answer("⚠️ Withdrawal is currently closed. Stay tuned!")

@dp.message(F.text == "🎁 Extra Earning")
async def extra(message: types.Message):
    await message.answer("🎁 No extra tasks available right now.")

@dp.message(F.text == "📈 Price Info")
async def price_info(message: types.Message):
    await message.answer("📈 USDT Price: 1 USDT = 120 BDT (Approx)")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
