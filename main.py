import asyncio
import os
import aiohttp
import aiosqlite

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
# ================= CONFIG =================

API_TOKEN = os.getenv("API_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL")

if not API_TOKEN:
    raise ValueError("API_TOKEN not found!")

CHANNELS = [
    "@USDT_GIVEAWAY_ii",
    "@USDT_GIVEAWAY_iii"
]

DB_PATH = "/var/data/bot_data.db"

# ================= BOT =================

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= STATES =================

class WithdrawState(StatesGroup):
    amount = State()
    method = State()
    address = State()

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
            balance INTEGER DEFAULT 0,
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

    uid = message.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            INSERT OR IGNORE INTO users(user_id)
            VALUES(?)
            """,
            (uid,)
        )

        await db.commit()

        await db.execute(
    """
    INSERT OR IGNORE INTO users(user_id)
    VALUES(?)
    """,
    (uid,)
)

        args = message.text.split()

        if len(args) > 1:
            try:
                referrer = int(args[1])

                if referrer != uid:

                    cur = await db.execute(
                        "SELECT * FROM referrals WHERE user_id=?",
                        (uid,)
                    )

                    exists = await cur.fetchone()

                    if not exists:

                        await db.execute(
                            "INSERT INTO referrals VALUES (?, ?)",
                            (uid, referrer)
                        )

                        await db.execute("""
                        UPDATE users
                        SET balance = balance + 100,
                            referrals = referrals + 1
                        WHERE user_id = ?
                        """, (referrer,))

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
        "🎁 Signup Bonus: 200 Coins\n"
        "🎁 Referral Bonus: 100 Coins\n\n"
        "Join all channels and click Verify.",
        reply_markup=keyboard
    )
    # ================= VERIFY CHANNEL =================

@dp.callback_query(F.data == "verify")
async def verify(callback: types.CallbackQuery):

    uid = callback.from_user.id

    try:

        for channel in CHANNELS:

            member = await bot.get_chat_member(
                channel,
                uid
            )

            if member.status in ["left", "kicked"]:
                return await callback.answer(
                    "❌ Please join all channels first!",
                    show_alert=True
                )

        async with aiosqlite.connect(DB_PATH) as db:

            cur = await db.execute(
                "SELECT verified FROM users WHERE user_id=?",
                (uid,)
            )

            row = await cur.fetchone()

            if row and row[0] == 1:
                return await callback.answer(
                    "⚠️ Bonus already claimed!",
                    show_alert=True
                )

            await db.execute("""
            UPDATE users
            SET balance = balance + 200,
                verified = 1
            WHERE user_id = ?
            """, (uid,))

            await db.commit()

        await callback.message.answer(
            "🎉 Congratulations!\n\n"
            "💰 200 Coins added successfully.",
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
            """
            SELECT balance, referrals
            FROM users
            WHERE user_id = ?
            """,
            (message.from_user.id,)
        )

        row = await cur.fetchone()

    if not row:
        return await message.answer(
            "❌ Account not found."
        )

    balance, refs = row

    await message.answer(
        f"👤 User ID: {message.from_user.id}\n\n"
        f"💰 Balance: {balance} Coins\n"
        f"👥 Total Referrals: {refs}",
        reply_markup=get_main_menu()
    )


# ================= REFER & EARN =================

@dp.message(F.text == "👥 Refer & Earn")
async def refer(message: types.Message):

    me = await bot.get_me()

    async with aiosqlite.connect(DB_PATH) as db:

        cur = await db.execute(
            """
            SELECT referrals
            FROM users
            WHERE user_id = ?
            """,
            (message.from_user.id,)
        )

        row = await cur.fetchone()

    refs = row[0] if row else 0

    link = (
        f"https://t.me/{me.username}"
        f"?start={message.from_user.id}"
    )

    await message.answer(
        f"🔗 Your Referral Link:\n\n"
        f"{link}\n\n"
        f"🎁 Referral Bonus: 100 Coins\n"
        f"👥 Total Referrals: {refs}",
        reply_markup=get_main_menu()
    )
    # ================= PRICE INFO =================

@dp.message(F.text == "📈 Price Info")
async def price_info(message: types.Message):

    await message.answer(
        "📈 Coin Price Information\n\n"
        "💵 100 Coins = $0.01\n\n"
        "💳 Minimum Withdraw: 10 Coins\n\n"
        "⚠️ Rates may change anytime.",
        reply_markup=get_main_menu()
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
        return await message.answer(
            "No leaderboard data found."
        )

    text = "🏆 Top Referrers\n\n"

    for i, row in enumerate(rows, start=1):

        text += (
            f"{i}. ID: `{row[0]}` "
            f"- {row[1]} referrals\n"
        )

    await message.answer(
        text,
        parse_mode="Markdown"
    )


# ================= WITHDRAW =================

@dp.message(F.text == "💳 Withdraw")
async def withdraw(message: types.Message, state: FSMContext):

    async with aiosqlite.connect(DB_PATH) as db:

        cur = await db.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (message.from_user.id,)
        )

        row = await cur.fetchone()

    balance = row[0] if row else 0

    if balance < 10:
        return await message.answer(
            f"❌ Minimum Withdraw: 10 Coins\n\n"
            f"💰 Your Balance: {balance} Coins"
        )

    await message.answer(
    f"💰 Your Balance: {balance} Coins\n\n"
    "Enter withdrawal amount:",
    reply_markup=ReplyKeyboardRemove()
)

    await state.set_state(WithdrawState.amount)


# ================= GET AMOUNT =================

@dp.message(WithdrawState.amount)
async def get_amount(message: types.Message,
                     state: FSMContext):

    if not message.text.isdigit():

        return await message.answer(
            "❌ Please enter numbers only."
        )

    amount = int(message.text)

    if amount < 10:

        return await message.answer(
            "❌ Minimum withdraw is 10 Coins."
        )

    async with aiosqlite.connect(DB_PATH) as db:

        cur = await db.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (message.from_user.id,)
        )

        row = await cur.fetchone()

    balance = row[0]

    if amount > balance:

        return await message.answer(
            "❌ Insufficient Balance."
        )

    await state.update_data(amount=amount)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="USDT BEP20")],
            [KeyboardButton(text="USDT TRC20")],
            [KeyboardButton(text="Binance ID")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "Choose withdrawal method:",
        reply_markup=kb
    )

    await state.set_state(
        WithdrawState.method
    )
                         # ================= GET METHOD =================

@dp.message(WithdrawState.method)
async def get_method(message: types.Message,
                     state: FSMContext):

    methods = [
        "USDT BEP20",
        "USDT TRC20",
        "Binance ID"
    ]

    if message.text not in methods:

        return await message.answer(
            "❌ Please select a valid method."
        )

    await state.update_data(
        method=message.text
    )

    if message.text == "Binance ID":
        txt = "Enter your Binance Pay ID:"
    else:
        txt = "Send your wallet address:"

    await message.answer(
        txt,
        reply_markup=ReplyKeyboardRemove()
    )

    await state.set_state(
        WithdrawState.address
    )


# ================= GET ADDRESS =================

@dp.message(WithdrawState.address)
async def get_address(message: types.Message,
                      state: FSMContext):

    data = await state.get_data()

    amount = data["amount"]
    method = data["method"]
    address = message.text

    usdt_amount = round(
        (amount / 100) * 0.01,
        6
    )

    payload = {
        "user_id": message.from_user.id,
        "username": message.from_user.username or "No Username",
        "amount": amount,
        "method": method,
        "address": address,
        "usdt": usdt_amount
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEB_APP_URL,
                json=payload
            ) as response:
                print(await response.text())

    except Exception as e:
        print("Apps Script Error:", e)

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ?
            """,
            (amount, message.from_user.id)
        )

        await db.commit()

    await message.answer(
        f"✅ Withdrawal Request Submitted\n\n"
        f"💰 Amount: {amount} Coins\n"
        f"💵 USDT: ${usdt_amount}\n"
        f"🏦 Method: {method}\n\n"
        "⏳ Status: Pending",
        reply_markup=get_main_menu()
    )

    await state.clear()


# ================= CANCEL =================

@dp.message(Command("cancel"))
async def cancel(message: types.Message,
                 state: FSMContext):

    await state.clear()

    await message.answer(
        "❌ Operation Cancelled.",
        reply_markup=get_main_menu()
    )


# ================= UNKNOWN MESSAGE =================

@dp.message()
async def unknown(message: types.Message):

    await message.answer(
        "Please use the menu buttons below.",
        reply_markup=get_main_menu()
    )


# ================= MAIN =================

async def main():

    await init_db()

    print("✅ Bot Started Successfully")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
