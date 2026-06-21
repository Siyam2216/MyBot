import asyncio
import aiosqlite
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest

API_TOKEN = os.environ.get('API_TOKEN')
CHANNEL_1 = "@USDT_GIVEAWAY_ii"
CHANNEL_2 = "@USDT_GIVEAWAY_iii"
# অটো-পোস্টের জন্য চ্যানেলের ইউজারনেম
CHANNEL_ID = "@USDT_GIVEAWAY_iii"
DB_PATH = "/var/data/bot_data.db"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
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
        [KeyboardButton(text="💳 Withdraw"), KeyboardButton(text="📈 Price Info")],
        [KeyboardButton(text="🏆 Leaderboard")]
    ], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 else None
    user_id = message.from_user.id
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance, referred_by) VALUES (?, ?, ?)", 
                         (user_id, 0.0, referrer_id))
        await db.commit()
    await message.answer("👋 Welcome! Please join our channels to claim your bonus:", reply_markup=get_join_keyboard())

@dp.message(F.text == "👤 Account")
async def account(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            await message.answer(f"👤 User ID: {message.from_user.id}\n💰 Current Balance: {balance} Coins")

@dp.message(F.text == "👥 Refer & Earn")
async def refer(message: types.Message):
    bot_username = (await bot.get_me()).username
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (message.from_user.id,)) as cursor:
            refer_count = (await cursor.fetchone())[0]
    await message.answer(f"🔥 **Boost Your Earnings!**\n\n"
                         f"Share your link and reach 20 referrals to unlock instant withdrawal!\n\n"
                         f"🔗 **Link:** https://t.me/{bot_username}?start={message.from_user.id}\n\n"
                         f"👥 **Total Referrals:** {refer_count}\n"
                         f"💰 **Earn:** 100 Coins per referral!")

@dp.message(F.text == "💳 Withdraw")
async def withdraw(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (message.from_user.id,)) as cursor:
            refer_count = (await cursor.fetchone())[0]
    target = 20
    remaining = target - refer_count
    if refer_count >= target:
        await message.answer("✅ **Withdrawal Open!**\n\nYou have completed 20+ referrals. Please enter your USDT (TRC20) address to proceed.")
    else:
        await message.answer(f"🚫 **Withdrawal Locked!**\n\nYou need 20 referrals to unlock withdrawal.\n\n📊 **Your Progress:** {refer_count}/20\n🚀 Only {remaining} referrals left!")

@dp.message(F.text == "📈 Price Info")
async def price(message: types.Message):
    await message.answer("📈 **Price Prediction:** 0.01 USDT to 1.00 USDT based on total volume. 🗓 Official price set on 1st July.")

@dp.message(F.text == "🏆 Leaderboard")
async def show_leaderboard(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT referred_by, COUNT(*) as count FROM users WHERE referred_by IS NOT NULL GROUP BY referred_by ORDER BY count DESC LIMIT 10")
        rows = await cursor.fetchall()
    text = "🏆 **Top 10 Referrers Leaderboard:**\n\n"
    for i, (ref_id, count) in enumerate(rows, 1):
        text += f"{i}. User `{ref_id}` — {count} Referrals\n"
    await message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data == "verify_join")
async def verify(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] >= 200:
                await callback.answer("❌ You already claimed your bonus!", show_alert=True)
                return

    if await check_subscription(user_id, CHANNEL_1) and await check_subscription(user_id, CHANNEL_2):
        await callback.message.delete()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = balance + 200 WHERE user_id = ?", (user_id,))
            cursor = await db.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            referrer_id = row[0] if row else None
            if referrer_id:
                await db.execute("UPDATE users SET balance = balance + 100 WHERE user_id = ?", (referrer_id,))
                try: await bot.send_message(referrer_id, "🎉 Congratulations! You received 100 coins bonus from a referral.")
                except: pass
            await db.commit()
        # অটো পোস্ট
        try: await bot.send_message(CHANNEL_ID, f"🎉 **New User Verified!**\nUser ID: `{user_id}` has joined and started earning! Join now: @{(await bot.get_me()).username}")
        except: pass
        await callback.message.answer("🎉 Congratulations! You received 200 coins as a welcome bonus!", reply_markup=get_main_menu())
    else:
        await callback.answer("❌ Join both channels first!", show_alert=True)

async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
