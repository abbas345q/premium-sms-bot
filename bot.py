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

# --- OTP LISTENER ---
@bot.message_handler(func=lambda m: m.chat.username == TARGET_GROUP_USERNAME or m.chat.id == -1002295608331)
def listen_otp_group(message):
    if not message.text: return
    text = message.text
    found_numbers = re.findall(r'\+?\d{10,16}', text)
    if found_numbers:
        for raw_num in found_numbers:
            full_num = f"+{raw_num.lstrip('+')}"
            try:
                parsed = phonenumbers.parse(full_num); c_code = str(parsed.country_code); last3 = full_num[-3:] 
                match_key = f"{c_code}_{last3}"
                current_orders = load_data(ORDERS_FILE, {})
                if match_key in current_orders:
                    for user_id in current_orders[match_key]:
                        otp_text = (f"🔔 **আপনার ওটিপি পাওয়া গেছে!**\n\n📱 নাম্বার: `{full_num}`\n✉️ মেসেজ: \n`{text}`")
                        try: bot.send_message(user_id, otp_text, parse_mode="Markdown")
                        except: pass
            except: continue

# --- BROADCAST ---
def do_broadcast(message):
    if message.text == "/cancel":
        bot.send_message(message.chat.id, "❌ বাতিল।")
        return
    all_users = load_data(USER_FILE, {})
    success = 0
    status_msg = bot.send_message(message.chat.id, "⏳ পাঠানো হচ্ছে...")
    for uid in all_users.keys():
        try:
            bot.send_message(uid, message.text)
            success += 1
            time.sleep(0.05) 
        except: continue
    bot.edit_message_text(f"✅ **User Message Send Success!**\n🚀 মোট `{success}` জন।", message.chat.id, status_msg.message_id, parse_mode="Markdown")

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['settings'])
def admin_settings(message):
    if int(message.from_user.id) != int(ADMIN_ID): return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💵 Set Refer Bonus", callback_data="conf_ref"),
        types.InlineKeyboardButton("🏧 Set Min Withdraw", callback_data="conf_with"),
        types.InlineKeyboardButton("🗑️ Clear Stock", callback_data="conf_clear"),
        types.InlineKeyboardButton("📢 Broadcast Message", callback_data="conf_bc"),
        types.InlineKeyboardButton("⚙️ Manage Channels", callback_data="conf_chan")
    )
    text = (f"🛠 **Admin Control Panel**\n\n💰 Refer Bonus: `{config['ref_bonus']}` BDT\n"
            f"🏧 Min Withdraw: `{config['min_withdraw']}` BDT\nSelect an option:")
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = str(message.from_user.id)
    name = message.from_user.first_name
    current_time = time.time()

    if not is_user_joined_all(message.from_user.id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(config['channels'], 1):
            markup.add(types.InlineKeyboardButton(f"📢 Join Channel {i}", url=ch['link']))
        markup.add(types.InlineKeyboardButton("✅ I've Joined - Verify", callback_data="verify_join"))
        bot.send_message(message.chat.id, f"✨ **Welcome {name}!**\n\nসার্ভিসটি ব্যবহার করতে নিচের চ্যানেলে অবশ্যই জয়েন করুন।", reply_markup=markup, parse_mode="Markdown")
        return

    # রেফারাল
    args = message.text.split()
    if len(args) > 1 and uid not in users:
        ref_id = args[1]
        if ref_id in users and ref_id != uid:
            users[ref_id]['balance'] += config['ref_bonus']
            users[ref_id]['ref_count'] += 1
            save_data(USER_FILE, users)
            bot.send_message(ref_id, f"🎊 **New Referral!** You earned {config['ref_bonus']} BDT.")

    u_data = get_user(message.from_user.id, name)
    if current_time - u_data.get('last_start_time', 0) > 86400:
        users[uid]['last_start_time'] = current_time
        save_data(USER_FILE, users)
        welcome_text = (
    f"👑 **Welcome , {name}!**\n"
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"🌟 **Premium OTP & SMS Hub**-এ আপনাকে স্বাগতম।\n\n"
    f"🚀 **আমাদের বিশেষত্ব:**\n"
    f"⚡️ আল্ট্রা-ফাস্ট ওটিপি ডেলিভারি সিস্টেম।\n"
    f"🌍 বিশ্বের ১০০+ দেশের নাম্বার ।\n"
    f"🛡 ১০০% নিরাপদ এবং প্রাইভেট ট্রানজেকশন।\n\n"
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"📥 নিচের মেনু থেকে আপনার প্রয়োজনীয় সেবাটি বেছে নিন।"
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_keyboard(), parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "⚡ **Bot Restarted!**", reply_markup=main_keyboard(), parse_mode="Markdown")

@bot.message_handler(content_types=['text', 'document'])
def handle_all_messages(message):
    if not is_user_joined_all(message.from_user.id):
        handle_start(message)
        return
    if message.text and message.text.startswith('/'): return
    uid = str(message.from_user.id)
    u_data = get_user(message.from_user.id)

    if message.text == "📞 Get Number": send_country_list(message.chat.id)
    elif message.text == "💰 Balance":
        bot.send_message(message.chat.id, f"💳 **Wallet:**\n💰 Balance: `{u_data['balance']} BDT`", parse_mode="Markdown")
    elif message.text == "🎁 Refer & Earn":
        bot_user = (bot.get_me()).username
        bot.send_message(message.chat.id, f"📢 **Referral:**\n🔗 https://t.me/{bot_user}?start={uid}")
    elif message.text == "💸 Withdraw":
        bot.send_message(message.chat.id, f"❌ **Min withdraw:** {config['min_withdraw']} BDT.")
    elif message.text == "🌍 Available Countries":
        current_db = load_data(DB_FILE, {})
        active = [f"✅ {k} (Stock: {len(v)})" for k, v in current_db.items() if v and len(v) > 0]
        bot.send_message(message.chat.id, "🌍 **Stock:**\n\n" + "\n".join(active) if active else "❌ Empty", parse_mode="Markdown")
    
    elif message.from_user.id == ADMIN_ID:
        txt = message.text
        if message.content_type == 'document':
            f_info = bot.get_file(message.document.file_id)
            txt = (bot.download_file(f_info.file_path)).decode('utf-8')
        
        if txt:
            found = re.findall(r'\d{7,16}', txt)
            added = 0
            current_db = load_data(DB_FILE, {})
            for raw in found:
                c_name = detect_country(raw); num = f"+{raw.lstrip('+')}"
                if c_name not in current_db: current_db[c_name] = []
                if num not in current_db[c_name]: current_db[c_name].append(num); added += 1
            save_data(DB_FILE, current_db); bot.reply_to(message, f"✅ Added {added} numbers.")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    bot.answer_callback_query(call.id)
    uid = str(call.from_user.id)
    if call.data == "verify_join":
        if is_user_joined_all(call.from_user.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            handle_start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ আপনি সব চ্যানেলে জয়েন করেননি!", show_alert=True)
    elif call.data == "conf_chan":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("➕ Add New Channel", callback_data="add_chan"))
        for i, ch in enumerate(config['channels']):
            markup.add(types.InlineKeyboardButton(f"🗑️ Delete {ch['username']}", callback_data=f"delchan_{i}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_admin"))
        bot.edit_message_text("⚙️ **Manage Channels:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif call.data == "add_chan":
        msg = bot.send_message(call.message.chat.id, "⌨️ Send `@Username Link` (Example: `@MyGroup https://t.me/MyGroup`)")
        bot.register_next_step_handler(msg, process_add_chan)
    elif call.data.startswith("delchan_"):
        idx = int(call.data.split("_")[1]); config['channels'].pop(idx); save_data(CONFIG_FILE, config); handle_query(call)
    elif call.data == "back_admin":
        bot.delete_message(call.message.chat.id, call.message.message_id); admin_settings(call.message)
    elif call.data == "conf_bc":
        msg = bot.send_message(call.message.chat.id, "📢 Send Broadcast:"); bot.register_next_step_handler(msg, do_broadcast)
    elif call.data == "conf_ref":
        msg = bot.send_message(call.message.chat.id, "Refer Bonus:"); bot.register_next_step_handler(msg, update_ref)
    elif call.data == "conf_with":
        msg = bot.send_message(call.message.chat.id, "Min Withdraw:"); bot.register_next_step_handler(msg, update_with)
    elif call.data == "conf_clear":
        current_db = load_data(DB_FILE, {})
        markup = types.InlineKeyboardMarkup()
        for k in current_db.keys():
            if current_db[k]: markup.add(types.InlineKeyboardButton(f"🗑️ {k}", callback_data=f"rmv_{k}"))
        bot.edit_message_text("Clear stock:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif call.data.startswith('rmv_'):
        c = call.data.replace('rmv_', ''); current_db = load_data(DB_FILE, {}); current_db[c] = []
        save_data(DB_FILE, current_db); admin_settings(call.message)
    elif call.data.startswith('sel_'):
        if not is_user_joined_all(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ জয়েন করেননি!", show_alert=True); return
        country = call.data.replace('sel_', ''); current_db = load_data(DB_FILE, {})
        if country in current_db and current_db[country]:
            num = current_db[country].pop(0); save_data(DB_FILE, current_db)
            try:
                parsed = phonenumbers.parse(num); c_code = str(parsed.country_code); l3 = num[-3:]; m_key = f"{c_code}_{l3}"
                order_db = load_data(ORDERS_FILE, {})
                if m_key not in order_db: order_db[m_key] = []
                if uid not in order_db[m_key]: order_db[m_key].append(uid)
                save_data(ORDERS_FILE, order_db)
            except: pass
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("🔄 CHANGE NUMBER", callback_data=f"sel_{country}"),
                       types.InlineKeyboardButton("🌐 CHANGE COUNTRY", callback_data="back_c"),
                       types.InlineKeyboardButton("🚀 GET OTP", url=OTP_GROUP_LINK))
            bot.edit_message_text(f"🎁 **Number for {country.upper()}**\n━━━━━━━━━━━━━━\n`{num}`\n━━━━━━━━━━━━━━\n💡 Tap to copy!", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif call.data == "back_c": send_country_list(call.message.chat.id, call.message.message_id)

def process_add_chan(message):
    try:
        parts = message.text.split()
        if len(parts) < 2: raise Exception()
        config['channels'].append({"username": parts[0], "link": parts[1]})
        save_data(CONFIG_FILE, config); bot.send_message(message.chat.id, f"✅ Added {parts[0]}!")
    except: bot.send_message(message.chat.id, "❌ Error. Use: `@Username Link`")

def update_ref(message):
    try: config['ref_bonus'] = float(message.text); save_data(CONFIG_FILE, config); bot.send_message(message.chat.id, "✅ Updated")
    except: bot.send_message(message.chat.id, "❌ Error")
def update_with(message):
    try: config['min_withdraw'] = float(message.text); save_data(CONFIG_FILE, config); bot.send_message(message.chat.id, "✅ Updated")
    except: bot.send_message(message.chat.id, "❌ Error")
def send_country_list(chat_id, message_id=None):
    # ফাইল থেকে লেটেস্ট ডাটা লোড করা নিশ্চিত করা
    current_db = load_data(DB_FILE, {})
    active = {k: v for k, v in current_db.items() if isinstance(v, list) and len(v) > 0}
    
    if not active:
        bot.send_message(chat_id, "❌ বর্তমানে কোনো নাম্বার স্টক নেই।")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for c in sorted(active.keys()):
        markup.add(types.InlineKeyboardButton(f"{c} ({len(active[c])})", callback_data=f"sel_{c}"))
    
    if message_id:
        try: bot.edit_message_text("📍 **Select Country:**", chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        except: pass
    else:
        bot.send_message(chat_id, "📍 **Select Country:**", reply_markup=markup, parse_mode="Markdown")

if __name__ == "__main__":
    print("--- PREMIUM BOT IS ONLINE ---")
    # ক্লাউডে বট রানিং রাখার জন্য infinity_polling ব্যবহার করা হয়েছে
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
                                         
