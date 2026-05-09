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
config = load_data(CONFIG_FILE, {"ref_bonus": 5.0, "min_withdraw": 500.0, "channels": DEFAULT_CHANNELS})
users = load_data(USER_FILE, {})

def get_user(user_id, name="User"):
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"balance": 0.0, "ref_count": 0, "name": name}
        save_data(USER_FILE, users)
    return users[uid]

def is_user_joined_all(user_id):
    if not config['channels']: return True
    for ch in config['channels']:
        try:
            member = bot.get_chat_member(ch['username'], user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

# --- KEYBOARDS ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("📞 Get Number"), types.KeyboardButton("💰 Balance"))
    markup.row(types.KeyboardButton("🎁 Refer & Earn"), types.KeyboardButton("💸 Withdraw"))
    markup.row(types.KeyboardButton("🌍 Available Countries"))
    return markup

def detect_country(num_str):
    try:
        full_num = f"+{num_str.lstrip('+')}"
        parsed = phonenumbers.parse(full_num)
        region = phonenumbers.region_code_for_number(parsed)
        name = geocoder.description_for_number(parsed, "en")
        flag = "".join(chr(ord(c) + 127397) for c in region.upper()) if region else "📍"
        return f"{flag} {name}" if name else f"📍 Zone +{parsed.country_code}"
    except: return f"📍 Zone +{num_str[:3]}"

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = str(message.from_user.id)
    if not is_user_joined_all(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for i, ch in enumerate(config['channels'], 1):
            markup.add(types.InlineKeyboardButton(f"📢 Join {i}", url=ch['link']))
        markup.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify_join"))
        bot.send_message(message.chat.id, "Welcome! Please join our channels.", reply_markup=markup)
        return
    get_user(message.from_user.id, message.from_user.first_name)
    bot.send_message(message.chat.id, "👑 Premium SMS Panel", reply_markup=main_keyboard())

@bot.message_handler(content_types=['text', 'document'])
def handle_all(message):
    if not is_user_joined_all(message.from_user.id): return
    uid = str(message.from_user.id)
    if message.text == "📞 Get Number": send_country_list(message.chat.id)
    elif message.text == "💰 Balance":
        u = get_user(uid)
        bot.send_message(message.chat.id, f"💳 Balance: {u['balance']} BDT")
    elif message.from_user.id == ADMIN_ID:
        txt = message.text if message.text else ""
        if message.content_type == 'document':
            f_info = bot.get_file(message.document.file_id)
            txt = bot.download_file(f_info.file_path).decode('utf-8')
        found = re.findall(r'\d{7,16}', txt)
        if found:
            curr_db = load_data(DB_FILE, {})
            added = 0
            for r in found:
                c = detect_country(r); n = f"+{r.lstrip('+')}"
                if c not in curr_db: curr_db[c] = []
                if n not in curr_db[c]: curr_db[c].append(n); added += 1
            save_data(DB_FILE, curr_db)
            bot.reply_to(message, f"✅ Added {added} numbers.")

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
        curr_db = load_data(DB_FILE, {})
        
        if country in curr_db and curr_db[country]:
            num = curr_db[country].pop(0)
            save_data(DB_FILE, curr_db)
            
            # অর্ডার ট্র্যাকিং
            try:
                p = phonenumbers.parse(num)
                m_key = f"{p.country_code}_{str(num)[-3:]}"
                o_db = load_data(ORDERS_FILE, {})
                if m_key not in o_db: o_db[m_key] = []
                o_db[m_key].append(uid)
                save_data(ORDERS_FILE, o_db)
            except: pass

            markup = types.InlineKeyboardMarkup(row_width=1)
            # --- কপি বাটন (এটি সরাসরি কাজ করবে) ---
            try:
                markup.add(types.InlineKeyboardButton(text=f"📱 {num}", copy_text=num))
            except:
                markup.add(types.InlineKeyboardButton(text=f"📱 {num} (Copy)", callback_data="none"))
            
            markup.add(
                types.InlineKeyboardButton("🔄 CHANGE NUMBER", callback_data=f"sel_{country}"),
                types.InlineKeyboardButton("🌐 CHANGE COUNTRY", callback_data="back_c"),
                types.InlineKeyboardButton("🚀 GET OTP", url=OTP_GROUP_LINK)
            )
            
            # কোনো Markdown ছাড়াই টেক্সট যাতে এরর না হয়
            msg_text = f"🎁 Number for: {country}\n\nNumber: {num}\n\n💡 Tap the button above to copy the number."
            
            try:
                bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
            except:
                # এডিট এরর দিলে নতুন করে মেসেজ পাঠাবে
                bot.send_message(call.message.chat.id, msg_text, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "Stock Empty!", show_alert=True)

    elif call.data == "back_c":
        send_country_list(call.message.chat.id, call.message.message_id)

def send_country_list(chat_id, message_id=None):
    curr_db = load_data(DB_FILE, {})
    active = {k: v for k, v in curr_db.items() if isinstance(v, list) and len(v) > 0}
    
    if not active:
        bot.send_message(chat_id, "❌ No stock available.")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for c in sorted(active.keys()):
        markup.add(types.InlineKeyboardButton(f"{c} ({len(active[c])})", callback_data=f"sel_{c}"))
    
    txt = "📍 Select Country:"
    if message_id:
        try: bot.edit_message_text(txt, chat_id, message_id, reply_markup=markup)
        except: pass
    else:
        bot.send_message(chat_id, txt, reply_markup=markup)

if __name__ == "__main__":
    bot.infinity_polling()
    
