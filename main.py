import asyncio
import logging
import aiosqlite
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest

API_TOKEN = os.environ.get('API_TOKEN')
CHANNEL_1 = "@USDT_GIVEAWAY_ii"
CHANNEL_2 = "@USDT_GIVEAWAY_iii"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def init_db():
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
                          (user_id INTEGER PRIMARY KEY, balance REAL, referred_by INTEGER)''')
        await db.commit()

async def check_subscription(user_id, channel):
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except TelegramBadRequest:
        return False

def get_join_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Join Channel 1", url="https://t.me/USDT_GIVEAWAY_ii")],
        [InlineKeyboardButton(text="Join Channel 2", url="https://t.me/USDT_GIVEAWAY_iii")],
        [InlineKeyboardButton(text="✅ Verify & Claim", callback_data="verify_join")]
    ])

def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Account"), KeyboardButton(text="👥 Refer & Earn")],
        [KeyboardButton(text="💳 Withdraw"), KeyboardButton(text="📈 Price Info")]
    ], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 else None
    user_id = message.from_user.id
    
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance, referred_by) VALUES (?, ?, ?)", 
                         (user_id, 0.0, referrer_id))
        await db.commit()
    await message.answer("👋 Welcome! Please join our channels to claim your bonus:", reply_markup=get_join_keyboard())

# --- নতুন যুক্ত করা হ্যান্ডলারগুলো ---

@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            await message.answer(f"👤 User ID: {message.from_user.id}\n💰 Current Balance: {balance} Coins")

@dp.message(F.text == "👥 Refer & Earn")
async def refer(message: types.Message):
    await message.answer(f"🔗 Your referral link: https://t.me/{(await bot.get_me()).username}?start={message.from_user.id}\n\nShare this link to earn 50 coins per referral!")

@dp.message(F.text == "💳 Withdraw")
async def withdraw(message: types.Message):
    await message.answer("⏳ Withdrawal is locked. It will open on 1st July.")

@dp.message(F.text == "📈 Price Info")
async def price(message: types.Message):
    await message.answer("📈 Price Prediction: 0.1 BDT to 1000 BDT based on total volume.")

# --- ভেরিফিকেশন হ্যান্ডলার ---
@dp.callback_query(F.data == "verify_join")
async def verify(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id, CHANNEL_1) and await check_subscription(callback.from_user.id, CHANNEL_2):
        await callback.message.delete()
        async with aiosqlite.connect('bot_data.db') as db:
            await db.execute("UPDATE users SET balance = balance + 200 WHERE user_id = ?", (callback.from_user.id,))
            await db.commit()
        await callback.message.answer("🎉 Congratulations! Received 200 coins.", reply_markup=get_main_menu())
    else:
        await callback.answer("❌ Join both channels first!", show_alert=True)

async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
