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

bot = telebot.TeleBot(API_TOKEN, threaded=False)

# --- DATA PERSISTENCE ---
def load_data(file, default):
    if os.path.exists(file):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return default
    return default

def save_data(file, data):
    try:
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except: pass

config = load_data(CONFIG_FILE, {"ref_bonus": 2.0, "min_withdraw": 500.0, "channels": []})
users = load_data(USER_FILE, {})

def get_user(user_id, name="User"):
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"balance": 0.0, "ref_count": 0, "name": name, "joined": True}
        save_data(USER_FILE, users)
        return users[uid], True
    return users[uid], False

def is_user_joined_all(user_id):
    if not config.get('channels'): return True
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

def detect_country_info(num_str):
    try:
        full_num = f"+{num_str.lstrip('+')}"
        parsed = phonenumbers.parse(full_num)
        name = geocoder.description_for_number(parsed, "en")
        region = phonenumbers.region_code_for_number(parsed)
        flag = "".join(chr(ord(c) + 127397) for c in region.upper()) if region else "📍"
        return flag, name if name else f"Zone +{parsed.country_code}"
    except: return "📍", f"Zone +{num_str[:3]}"

def send_country_list(chat_id, message_id=None):
    curr_db = load_data(DB_FILE, {})
    active = {k: v for k, v in curr_db.items() if isinstance(v, list) and len(v) > 0}
    if not active:
        bot.send_message(chat_id, "❌ No stock available.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for c in sorted(active.keys()):
        markup.add(types.InlineKeyboardButton(f"{c} ({len(active[c])})", callback_data=f"sel_{c}"))
    
    txt = "📍 **Select Country:**"
    if message_id:
        try: bot.edit_message_text(txt, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        except: bot.send_message(chat_id, txt, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, txt, reply_markup=markup, parse_mode="Markdown")

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = str(message.from_user.id)
    if not is_user_joined_all(message.from_user.id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(config.get('channels', []), 1):
            markup.add(types.InlineKeyboardButton(f"📢 Join Channel {i}", url=ch['link']))
        markup.add(types.InlineKeyboardButton("✅ Verify Join", callback_data="verify_join"))
        bot.send_message(message.chat.id, "✨ **সার্ভিসটি ব্যবহার করতে জয়েন করুন।**", reply_markup=markup)
        return
    u_data, is_new = get_user(message.from_user.id, message.from_user.first_name)
    if is_new:
        bot.send_message(message.chat.id, f"👑 **Welcome!**\nPremium OTP প্যানেলে স্বাগতম।", reply_markup=main_keyboard())
    else:
        send_country_list(message.chat.id)

@bot.message_handler(commands=['settings'])
def admin_settings(message):
    if int(message.from_user.id) != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💵 Set Refer Bonus", callback_data="conf_ref"),
        types.InlineKeyboardButton("🏧 Set Min Withdraw", callback_data="conf_with"),
        types.InlineKeyboardButton("🗑️ Clear Stock", callback_data="conf_clear"),
        types.InlineKeyboardButton("📢 Broadcast Message", callback_data="conf_bc"),
        types.InlineKeyboardButton("⚙️ Manage Channels", callback_data="conf_chan")
    )
    bot.send_message(message.chat.id, "🛠 **Admin Control Panel**", reply_markup=markup)

@bot.message_handler(content_types=['text', 'document'])
def handle_all(message):
    if not is_user_joined_all(message.from_user.id): return
    uid = str(message.from_user.id)
    u_data = load_data(USER_FILE, {}).get(uid, {"balance": 0.0})

    if message.text == "📞 Get Number":
        send_country_list(message.chat.id)
    elif message.text == "💰 Balance":
        bot.send_message(message.chat.id, f"💳 Balance: {u_data['balance']} BDT")
    elif message.text == "🎁 Refer & Earn":
        bot_user = (bot.get_me()).username
        bot.send_message(message.chat.id, f"🎁 **Refer Link:** https://t.me/{bot_user}?start={uid}")
    elif message.text == "💸 Withdraw":
        bot.send_message(message.chat.id, f"❌ Min Withdraw: {config['min_withdraw']} BDT")
    elif message.text == "🌍 Available Countries":
        current_db = load_data(DB_FILE, {})
        active = [f"✅ {k} ({len(v)})" for k, v in current_db.items() if v and len(v) > 0]
        bot.send_message(message.chat.id, "🌍 **Stock List:**\n\n" + "\n".join(active) if active else "Empty")
    
    elif int(message.from_user.id) == ADMIN_ID:
        txt = message.text if message.text else ""
        if message.content_type == 'document':
            f_info = bot.get_file(message.document.file_id)
            txt = bot.download_file(f_info.file_path).decode('utf-8')
        found = re.findall(r'\d{7,16}', txt)
        if found:
            curr_db = load_data(DB_FILE, {})
            added = 0
            for r in found:
                flag, name = detect_country_info(r)
                c_name = f"{flag} {name}"
                if c_name not in curr_db: curr_db[c_name] = []
                num = f"+{r.lstrip('+')}"
                if num not in curr_db[c_name]: curr_db[c_name].append(num); added += 1
            save_data(DB_FILE, curr_db)
            bot.reply_to(message, f"✅ Added {added} numbers.")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = str(call.from_user.id)
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data == "verify_join":
        if is_user_joined_all(call.from_user.id):
            bot.delete_message(chat_id, message_id)
            handle_start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ জয়েন করেননি!", show_alert=True)

    elif call.data.startswith('sel_'):
        country = call.data.replace('sel_', '')
        curr_db = load_data(DB_FILE, {})
        
        if country in curr_db and curr_db[country]:
            num = str(curr_db[country].pop(0))
            save_data(DB_FILE, curr_db)
            
            # কিবোর্ড (নম্বর বাটন ছাড়া)
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("🔄 CHANGE NUMBER", callback_data=f"sel_{country}"),
                types.InlineKeyboardButton("🌐 CHANGE COUNTRY", callback_data="back_c"),
                types.InlineKeyboardButton("🚀 GET OTP", url=OTP_GROUP_LINK)
            )
            
            # নম্বরটি সরাসরি টেক্সটে Mono আকারে দেওয়া হলো
            msg_text = f"🎁 **Number for: {country}**\n\n📱 Number: `{num}`\n\n💡 উপরের নাম্বারের ওপর ক্লিক করলেই কপি হয়ে যাবে।"
            try:
                bot.edit_message_text(text=msg_text, chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode="Markdown")
            except:
                bot.send_message(chat_id, msg_text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "❌ স্টক শেষ!", show_alert=True)

    elif call.data == "back_c":
        send_country_list(chat_id, message_id)

    elif call.data == "conf_chan":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("➕ Add Channel", callback_data="add_ch"))
        for i, ch in enumerate(config.get('channels', [])):
            markup.add(types.InlineKeyboardButton(f"🗑️ Delete {ch['username']}", callback_data=f"delch_{i}"))
        bot.edit_message_text("⚙️ Manage Channels:", chat_id, message_id, reply_markup=markup)

    elif call.data == "conf_bc":
        msg = bot.send_message(chat_id, "📢 Send Broadcast Message:")
        bot.register_next_step_handler(msg, lambda m: [bot.send_message(u, m.text) for u in users.keys()])

if __name__ == "__main__":
    bot.infinity_polling()
    
