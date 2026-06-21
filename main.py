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

API_TOKEN = os.getenv("API_TOKEN")

CHANNELS = [
    "@USDT_GIVEAWAY_ii",
    "@USDT_GIVEAWAY_iii"
]

DB_PATH = "bot_data.db"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Account"),
             KeyboardButton(text="👥 Refer & Earn")],

            [KeyboardButton(text="💳 Withdraw"),
             KeyboardButton(text="📈 Price Info")],

            [KeyboardButton(text="🏆 Leaderboard")]
        ],
        resize_keyboard=True
    )


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


@dp.message(Command("start"))
async def start(message: types.Message):

    user_id = message.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:

        # User exists?
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

        # Referral system
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

                        await db.execute(
                            """
                            UPDATE users
                            SET balance = balance + 50,
                                referrals = referrals + 1
                            WHERE user_id = ?
                            """,
                            (referrer_id,)
                        )

            except:
                pass

        await db.commit()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📢 Channel 1",
                url="https://t.me/USDT_GIVEAWAY_ii"
            )],

            [InlineKeyboardButton(
                text="📢 Channel 2",
                url="https://t.me/USDT_GIVEAWAY_iii"
            )],

            [InlineKeyboardButton(
                text="✅ Verify Join",
                callback_data="verify"
            )]
        ]
    )

    await message.answer(
        "👋 Welcome!\n\nJoin all channels then click Verify.",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "verify")
async def verify(callback: types.CallbackQuery):

    user_id = callback.from_user.id

    try:

        # Check channel membership
        for channel in CHANNELS:

            member = await bot.get_chat_member(
                channel,
                user_id
            )

            if member.status in ["left", "kicked"]:
                return await callback.answer(
                    "❌ Please join all channels first!",
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
                    "⚠️ Reward already claimed!",
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
            "🎉 Successfully verified!\n\n💰 200 Coins added.",
            reply_markup=get_main_menu()
        )

        await callback.answer()

    except Exception as e:
        print(e)

        await callback.answer(
            "❌ Verification failed.",
            show_alert=True
        )


@dp.message(F.text == "👥 Refer & Earn")
async def refer_info(message: types.Message):

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
        f"🔗 Your Referral Link:\n{link}\n\n"
        f"👥 Total Referrals: {refs}",
        reply_markup=get_main_menu()
    )


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
            f"👤 User ID: {message.from_user.id}\n"
            f"💰 Balance: {balance} Coins\n"
            f"👥 Referrals: {refs}"
        )


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
