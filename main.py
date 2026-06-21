import asyncio
import os
import aiosqlite

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ================= CONFIG =================

API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    raise ValueError("API_TOKEN not found!")

CHANNELS = [
    "@USDT_GIVEAWAY_ii",
    "@USDT_GIVEAWAY_iii"
]

DB_PATH = "bot_data.db"

# ================= BOT =================

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= MENU =================

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👤 Account"),
                KeyboardButton(text="👥 Refer & Earn")
            ],
            [
                KeyboardButton(text="💳 Withdraw"),
                KeyboardButton(text="📈 Price Info")
            ],
            [
                KeyboardButton(text="🏆 Leaderboard")
            ]
        ],
        resize_keyboard=True
    )

# ================= DATABASE =================

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            verified INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS referrals(
            user_id INTEGER PRIMARY KEY,
            referred_by INTEGER
        )
        """)

        await db.commit()

# ================= START =================

@dp.message(Command("start"))
async def start(message: types.Message):

    user_id = message.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:

        cur = await db.execute(
            "SELECT user_id FROM users WHERE user_id=?",
            (user_id,)
        )

        user = await cur.fetchone()

        if not user:
            await db.execute(
                "INSERT INTO users(user_id) VALUES(?)",
                (user_id,)
            )

        args = message.text.split()

        if len(args) > 1:
            try:
                referrer_id = int(args[1])

                if referrer_id != user_id:

                    cur = await db.execute(
                        "SELECT * FROM referrals WHERE user_id=?",
                        (user_id,)
                    )

                    already = await cur.fetchone()

                    if not already:

                        await db.execute(
                            "INSERT INTO referrals(user_id,referred_by) VALUES(?,?)",
                            (user_id, referrer_id)
                        )

                        await db.execute("""
                            UPDATE users
                            SET balance = balance + 50,
                                referrals = referrals + 1
                            WHERE user_id = ?
                        """, (referrer_id,))

            except:
                pass

        await db.commit()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Channel 1",
                    url="https://t.me/USDT_GIVEAWAY_ii"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Channel 2",
                    url="https://t.me/USDT_GIVEAWAY_iii"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Verify Join",
                    callback_data="verify"
                )
            ]
        ]
    )

    await message.answer(
        "👋 Welcome!\n\n"
        "Join both channels and click Verify.",
        reply_markup=keyboard
    )

# ================= VERIFY =================

@dp.callback_query(F.data == "verify")
async def verify(callback: types.CallbackQuery):

    user_id = callback.from_user.id

    try:

        for channel in CHANNELS:

            member = await bot.get_chat_member(
                channel,
                user_id
            )

            if member.status in ["left", "kicked"]:
                return await callback.answer(
                    "❌ Join all channels first!",
                    show_alert=True
                )

        async with aiosqlite.connect(DB_PATH) as db:

            cur = await db.execute(
                "SELECT verified FROM users WHERE user_id=?",
                (user_id,)
            )

            row = await cur.fetchone()

            if row and row[0] == 1:
                return await callback.answer(
                    "⚠️ Already claimed!",
                    show_alert=True
                )

            await db.execute("""
                UPDATE users
                SET balance = balance + 200,
                    verified = 1
                WHERE user_id = ?
            """, (user_id,))

            await db.commit()

        await callback.message.answer(
            "🎉 Congratulations!\n\n"
            "You received 200 Coins.",
            reply_markup=get_main_menu()
        )

        await callback.answer()

    except Exception as e:
        print(e)

        await callback.answer(
            "❌ Verification failed!",
            show_alert=True
        )

# ================= ACCOUNT =================

@dp.message(F.text == "👤 Account")
async def account(message: types.Message):

    async with aiosqlite.connect(DB_PATH) as db:

        cur = await db.execute(
            "SELECT balance, referrals FROM users WHERE user_id=?",
            (message.from_user.id,)
        )

        row = await cur.fetchone()

    if row:

        balance, refs = row

        await message.answer(
            f"👤 User ID: {message.from_user.id}\n\n"
            f"💰 Balance: {balance} Coins\n"
            f"👥 Referrals: {refs}"
        )

# ================= REFER =================

@dp.message(F.text == "👥 Refer & Earn")
async def refer(message: types.Message):

    async with aiosqlite.connect(DB_PATH) as db:

        cur = await db.execute(
            "SELECT referrals FROM users WHERE user_id=?",
            (message.from_user.id,)
        )

        row = await cur.fetchone()

    refs = row[0] if row else 0

    me = await bot.get_me()

    link = f"https://t.me/{me.username}?start={message.from_user.id}"

    await message.answer(
        f"🔗 Your Referral Link:\n\n"
        f"{link}\n\n"
        f"👥 Total Referrals: {refs}"
    )

# ================= WITHDRAW =================

@dp.message(F.text == "💳 Withdraw")
async def withdraw(message: types.Message):

    async with aiosqlite.connect(DB_PATH) as db:

        cur = await db.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (message.from_user.id,)
        )

        row = await cur.fetchone()

    balance = row[0] if row else 0

    if balance < 1000:
        return await message.answer(
            f"❌ Minimum withdrawal is 1000 Coins.\n\n"
            f"Your Balance: {balance} Coins"
        )

    await message.answer(
        "💳 Withdrawal Available\n\n"
        "Minimum Withdraw: 1000 Coins\n"
        "100 Coins = 1 USDT\n\n"
        "Contact Admin: @admin_username"
    )

# ================= PRICE =================

@dp.message(F.text == "📈 Price Info")
async def price(message: types.Message):

    await message.answer(
        "📈 Coin Price Information\n\n"
        "100 Coins = 1 USDT\n"
        "500 Coins = 5 USDT\n"
        "1000 Coins = 10 USDT\n\n"
        "⚠️ Price may change anytime."
    )

# ================= LEADERBOARD =================

@dp.message(F.text == "🏆 Leaderboard")
async def leaderboard(message: types.Message):

    async with aiosqlite.connect(DB_PATH) as db:

        cur = await db.execute("""
            SELECT user_id, referrals
            FROM users
            ORDER BY referrals DESC
            LIMIT 10
        """)

        rows = await cur.fetchall()

    if not rows:
        return await message.answer("No leaderboard data found.")

    text = "🏆 Top Referrers\n\n"

    for i, row in enumerate(rows, start=1):
        text += (
            f"{i}. User ID: `{row[0]}` "
            f"- {row[1]} referrals\n"
        )

    await message.answer(
        text,
        parse_mode="Markdown"
    )

# ================= MAIN =================

async def main():
    await init_db()
    print("Bot Started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
