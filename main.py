import telebot
from telebot import types
import sqlite3

# Token setup
API_TOKEN = '8669911640:AAENfShmFH-PYDFNxMj0tkBvnV2AEsC-k6o'
bot = telebot.TeleBot(API_TOKEN)

CHANNEL_1 = '@USDT_GIVEAWAY_ii'
CHANNEL_2 = '@USDT_GIVEAWAY_iii'

# Database connection
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()

# Create table if not exists
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, balance INTEGER, referrer_id INTEGER, verified INTEGER)''')
conn.commit()

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("👤 Account", "👥 Refer & Earn", "💳 Withdraw", "🎁 Extra Earning", "📈 Price Info")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user_id, 0, ref, 0))
        conn.commit()
    
    if user and user[3] == 1:
        bot.send_message(message.chat.id, "👋 Welcome back! Main menu is active.", reply_markup=get_main_menu())
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📢 Join Channel 1", url="https://t.me/USDT_GIVEAWAY_ii"),
            types.InlineKeyboardButton("📢 Join Channel 2", url="https://t.me/USDT_GIVEAWAY_iii"),
            types.InlineKeyboardButton("✅ Verify & Claim", callback_data="verify")
        )
        bot.send_message(message.chat.id, "👋 Join our channels and verify to claim your 200 Coin Welcome Bonus!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify(call):
    user_id = call.from_user.id
    try:
        sub1 = bot.get_chat_member(CHANNEL_1, user_id).status in ['member', 'administrator', 'creator']
        sub2 = bot.get_chat_member(CHANNEL_2, user_id).status in ['member', 'administrator', 'creator']
        
        if sub1 and sub2:
            cursor.execute("SELECT verified, referrer_id FROM users WHERE user_id=?", (user_id,))
            row = cursor.fetchone()
            if row and row[0] == 0:
                cursor.execute("UPDATE users SET balance=balance + 200, verified=1 WHERE user_id=?", (user_id,))
                
                ref_id = row[1]
                if ref_id:
                    cursor.execute("UPDATE users SET balance=balance + 100 WHERE user_id=?", (ref_id,))
                    bot.send_message(ref_id, "🎉 Congratulations! You received a 100 Coin referral bonus.")
                
                conn.commit()
                bot.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, "✅ Channels Verified!\n🎉 200 Coin has been added to your account.", reply_markup=get_main_menu())
        else:
            bot.answer_callback_query(call.id, "❌ Please join both channels first!", show_alert=True)
    except:
        bot.answer_callback_query(call.id, "Error!")

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    user_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0
    text = message.text

    if text == "👤 Account":
        bot.reply_to(message, f"👤 Your Account Dashboard\n\n🆔 User ID: {user_id}\n💰 Current Balance: {balance} Coin")
    
    elif text == "👥 Refer & Earn":
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?start={user_id}"
        bot.reply_to(message, f"👥 Refer & Earn Program\n\n🔗 Your Referral Link: {link}\n🎁 Earn 100 Coin for every valid referral!")
        
    elif text == "💳 Withdraw":
        bot.reply_to(message, f"⚠️ Minimum withdrawal limit is 1000 Coin (Equivalent to $10.00 USDT).\n\n💰 Your Current Balance: {balance} Coin\n\n📢 Notice: Official withdrawal will be enabled starting July 1st.")
        
    elif text == "🎁 Extra Earning":
        bot.reply_to(message, "🚀 Extra Earning section will start soon! Stay tuned.")
        
    elif text == "📈 Price Info":
        info_msg = (
            "📈 **Coin Price Valuation Policy**\n\n"
            "Our coin's initial value starts from $0.10 and can reach up to $1000.00 USDT.\n"
            "The price depends entirely on our total volume of members and community activity.\n"
            "The more you refer, the higher the demand and value will rise!"
        )
        bot.reply_to(message, info_msg)
    
    else:
        bot.reply_to(message, "Please select an option from the menu.")

bot.remove_webhook()
print("Bot is running...")
bot.infinity_polling()