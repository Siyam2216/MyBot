import asyncio
import logging
import aiosqlite
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest

API_TOKEN = os.environ.get('API_TOKEN')
CHANNEL_1 = "@your_channel_username_1" # আপনার চ্যানেলের ইউজারনেম
CHANNEL_2 = "@your_channel_username_2"

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
        [InlineKeyboardButton(text="Join Channel 1", url=f"https://t.me/{CHANNEL_1[1:]}")],
        [InlineKeyboardButton(text="Join Channel 2", url=f"https://t.me/{CHANNEL_2[1:]}")],
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

@dp.callback_query(F.data == "verify_join")
async def verify(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await check_subscription(user_id, CHANNEL_1) and await check_subscription(user_id, CHANNEL_2):
        await callback.message.delete()
        
        # ওয়েলকাম বোনাস অ্যাড
        async with aiosqlite.connect('bot_data.db') as db:
            await db.execute("UPDATE users SET balance = balance + 200 WHERE user_id = ?", (user_id,))
            cursor = await db.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            referrer_id = row[0] if row else None
            
            # রেফারারকে বোনাস
            if referrer_id:
                await db.execute("UPDATE users SET balance = balance + 50 WHERE user_id = ?", (referrer_id,))
                try:
                    await bot.send_message(referrer_id, "🎉 Congratulations! You received 50 coins bonus from a referral.")
                except: pass
            await db.commit()
            
        await callback.message.answer("🎉 Congratulations! You received 200 coins as a welcome bonus!", reply_markup=get_main_menu())
    else:
        await callback.answer("❌ You haven't joined both channels yet!", show_alert=True)

async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
