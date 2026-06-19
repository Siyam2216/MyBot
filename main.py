import asyncio
import logging
import aiosqlite
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# API Token Render-এর এনভায়রনমেন্ট থেকে নেবে
API_TOKEN = os.environ.get('API_TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

async def init_db():
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
                          (user_id INTEGER PRIMARY KEY, balance REAL, referrer_id INTEGER, verified INTEGER)''')
        await db.commit()

def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Account"), KeyboardButton(text="👥 Refer & Earn")],
        [KeyboardButton(text="💳 Withdraw"), KeyboardButton(text="🎁 Extra Earning")],
        [KeyboardButton(text="📈 Price Info")]
    ], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect('bot_data.db') as db:
        # ইউজার যদি নতুন হয় তবে ব্যালেন্স ২০০ দিয়ে ইনসার্ট হবে
        async with db.execute("SELECT verified FROM users WHERE user_id=?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await db.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user_id, 200.0, None, 0))
                await db.commit()

            await message.answer("👋 Welcome back!", reply_markup=get_main_menu())

@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 200.0
            await message.answer(f"👤 User ID: {message.from_user.id}\n💰 Current Balance: {balance} USDT")

@dp.message(F.text == "👥 Refer & Earn")
async def refer(message: types.Message):
    bot_username = "usdtxtrustwallte_ttbbot"
    await message.answer(f"🔗 Your referral link:\nhttps://t.me/{bot_username}?start={message.from_user.id}\n\nShare this link to earn more!")

@dp.message(F.text == "💳 Withdraw")
async def withdraw(message: types.Message):
    await message.answer("💳 Withdraw is available after reaching 500 USDT.")

@dp.message(F.text == "🎁 Extra Earning")
async def extra(message: types.Message):
    await message.answer("🎁 Complete daily tasks to earn more USDT.")

@dp.message(F.text == "📈 Price Info")
async def price_info(message: types.Message):
    await message.answer("📈 USDT Price: 1 USDT = 120 BDT")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
