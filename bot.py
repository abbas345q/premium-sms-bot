import telebot
from telebot import types
import re
import json
import os
import time
import phonenumbers
from phonenumbers import geocoder

# --- CONFIGURATION ---
API_TOKEN = '7634786660:AAHvY09ndmYnO6pLpz_84rSLqGUEMlfwNd4'
ADMIN_ID = 6781949890
DB_FILE = 'numbers_db.json'
USER_FILE = 'users_data.json'
CONFIG_FILE = 'settings.json'
ORDERS_FILE = 'orders_db.json' 
OTP_GROUP_LINK = "https://t.me/Premium_OTP_chat"
TARGET_GROUP_USERNAME = "Premium_OTP_chat" 

bot = telebot.TeleBot(API_TOKEN, threaded=False)

# --- DATA PERSISTENCE ---
def load_data(file, default):
    if os.path.exists(file):
        try:
            with open(file, 'r') as f: return json.load(f)
        except: return default
    return default

def save_data(file, data):
    with open(file, 'w') as f: json.dump(data, f, indent=4)

DEFAULT_CHANNELS = [{"username": "@Earning_Tips055", "link": "https://t.me/Earning_Tips055"}]

db = load_data(DB_FILE, {})
users = load_data(USER_FILE, {})
orders = load_data(ORDERS_FILE, {}) 
config = load_data(CONFIG_FILE, {"ref_bonus": 5.0, "min_withdraw": 500.0, "channels": DEFAULT_CHANNELS})

if not config.get("channels"):
    config["channels"] = DEFAULT_CHANNELS
    save_data(CONFIG_FILE, config)

def get_user(user_id, name="User"):
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"balance": 0.0, "ref_count": 0, "name": name, "last_start_time": 0}
        save_data(USER_FILE, users)
    return users[uid]

def is_user_joined_all(user_id):
    if not config['channels']: return True
    for ch in config['channels']:
        try:
            member = bot.get_chat_member(ch['username'], user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except: return False
    return True

# --- KEYBOARDS ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("📞 Get Number"), types.KeyboardButton("💰 Balance"))
    markup.row(types.KeyboardButton("🎁 Refer & Earn"), types.KeyboardButton("💸 Withdraw"))
    markup.row(types.KeyboardButton("🌍 Available Countries"))
    return markup

# --- UTILS ---
def detect_country(num_str):
    try:
        full_num = f"+{num_str.lstrip('+')}"
        parsed = phonenumbers.parse(full_num)
        region = phonenumbers.region_code_for_number(parsed)
        name = geocoder.description_for_number(parsed, "en")
        flag = "".join(chr(ord(c) + 127397) for c in region.upper()) if region else "📍"
        return f"{flag} {name}" if name else f"📍 Zone +{parsed.country_code}"
    except: return f"📍 Zone +{num_str[:3]}"

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = str(message.from_user.id)
    name = message.from_user.first_name
    
    if not is_user_joined_all(message.from_user.id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(config['channels'], 1):
            markup.add(types.InlineKeyboardButton(f"📢 Join Channel {i}", url=ch['link']))
        markup.add(types.InlineKeyboardButton("✅ I've Joined - Verify", callback_data="verify_join"))
        bot.send_message(message.chat.id, f"✨ Welcome {name}!", reply_markup=markup)
        return

    get_user(message.from_user.id, name)
    bot.send_message(message.chat.id, "✅ Bot Started!", reply_markup=main_keyboard())

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text == "📞 Get Number":
        send_country_list(message.chat.id)
    elif message.text == "💰 Balance":
        u = get_user(message.from_user.id)
        bot.send_message(message.chat.id, f"💳 Balance: {u['balance']} BDT")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    bot.answer_callback_query(call.id)
    uid = str(call.from_user.id)
    
    if call.data == "verify_join":
        if is_user_joined_all(call.from_user.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            handle_start(call.message)
    
    elif call.data.startswith('sel_'):
        country = call.data.replace('sel_', '')
        current_db = load_data(DB_FILE, {})
        
        if country in current_db and len(current_db[country]) > 0:
            num = current_db[country].pop(0)
            save_data(DB_FILE, current_db)
            
            # অর্ডার সেভ করা (ওটিপি লিসেনারের জন্য)
            try:
                parsed = phonenumbers.parse(num)
                m_key = f"{parsed.country_code}_{str(num)[-3:]}"
                order_db = load_data(ORDERS_FILE, {})
                if m_key not in order_db: order_db[m_key] = []
                order_db[m_key].append(uid)
                save_data(ORDERS_FILE, order_db)
            except: pass

            # --- বাটন তৈরি ---
            markup = types.InlineKeyboardMarkup(row_width=1)
            try:
                # ডিরেক্ট কপি বাটন (এটিই আপনার মেইন রিকোয়ারমেন্ট)
                markup.add(types.InlineKeyboardButton(text=f"📱 {num}", copy_text=num))
            except:
                markup.add(types.InlineKeyboardButton(text=f"📱 {num}", callback_data="none"))

            markup.add(
                types.InlineKeyboardButton("🔄 CHANGE NUMBER", callback_data=f"sel_{country}"),
                types.InlineKeyboardButton("🌐 CHANGE COUNTRY", callback_data="back_c"),
                types.InlineKeyboardButton("🚀 GET OTP", url=OTP_GROUP_LINK)
            )
            
            # নিরাপদ টেক্সট (Markdown ছাড়া)
            msg_text = f"🎁 Number for {country.upper()}\n\nNumber: {num}\n\n💡 Tap the number button to copy!"
            
            try:
                bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
            except:
                bot.send_message(call.message.chat.id, msg_text, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ স্টক শেষ!", show_alert=True)

    elif call.data == "back_c":
        send_country_list(call.message.chat.id, call.message.message_id)

def send_country_list(chat_id, message_id=None):
    current_db = load_data(DB_FILE, {})
    active = {k: v for k, v in current_db.items() if isinstance(v, list) and len(v) > 0}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for c in sorted(active.keys()):
        markup.add(types.InlineKeyboardButton(f"{c} ({len(active[c])})", callback_data=f"sel_{c}"))
    
    if message_id:
        bot.edit_message_text("📍 Select Country:", chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, "📍 Select Country:", reply_markup=markup)

if __name__ == "__main__":
    bot.infinity_polling()
    
