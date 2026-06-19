import asyncio
import logging
import aiosqlite
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web

API_TOKEN = os.environ.get('API_TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# HTTP সার্ভার (Render পোর্ট সাপোর্ট)
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 8000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def init_db():
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
                          (user_id INTEGER PRIMARY KEY, balance REAL)''')
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
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await db.execute("INSERT INTO users VALUES (?, ?)", (user_id, 200.0))
                await db.commit()
    
    # এখানে শুধু একবার মেসেজ পাঠানো হচ্ছে
    await message.answer("👋 Welcome! Start referring to increase your coin value.", reply_markup=get_main_menu())

@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 200.0
            await message.answer(f"👤 User ID: {message.from_user.id}\n💰 Current Balance: {balance} Coins")

@dp.message(F.text == "👥 Refer & Earn")
async def refer(message: types.Message):
    bot_username = "usdtxtrustwallte_ttbbot"
    await message.answer(f"🔗 Your referral link:\nhttps://t.me/{bot_username}?start={message.from_user.id}\n\nShare this link to grow the community and increase coin price!")

@dp.message(F.text == "💳 Withdraw")
async def withdraw(message: types.Message):
    await message.answer("⏳ Withdrawal is currently locked. All withdrawals will open on **1st July** after the official price is set.")

@dp.message(F.text == "🎁 Extra Earning")
async def extra(message: types.Message):
    await message.answer("🎁 Complete daily tasks to boost your total balance.")

@dp.message(F.text == "📈 Price Info")
async def price_info(message: types.Message):
    await message.answer("📈 **আমাদের কয়েন সম্পর্কে তথ্য:**\n\n"
                         "আমাদের কয়েনের প্রাইস ০.১ টাকা থেকে শুরু করে ১০০০ টাকা পর্যন্ত হতে পারে। "
                         "এটি সম্পূর্ণভাবে আমাদের টোটাল মেম্বার ভলিউমের উপর নির্ভর করবে। "
                         "আপনি যত বেশি রেফার করবেন, কয়েনের রেট তত বাড়বে।\n\n"
                         "🗓 ১লা জুলাই প্রাইস নির্ধারণ করা হবে এবং সেদিন থেকেই সবাই উইথড্র (Withdraw) করতে পারবেন।")

async def main():
    await start_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
