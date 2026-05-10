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
            with open(file, 'r', encoding='utf-8') as f: return json.load(f)
        except: return default
    return default

def save_data(file, data):
    with open(file, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

DEFAULT_CHANNELS = [{"username": "@Earning_Tips055", "link": "https://t.me/Earning_Tips055"}]
config = load_data(CONFIG_FILE, {"ref_bonus": 2.0, "min_withdraw": 500.0, "channels": DEFAULT_CHANNELS})
users = load_data(USER_FILE, {})

def get_user(user_id, name="User"):
    uid = str(user_id)
    is_new = False
    if uid not in users:
        users[uid] = {"balance": 0.0, "ref_count": 0, "name": name, "joined": True}
        save_data(USER_FILE, users)
        is_new = True
    return users[uid], is_new

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
    name = message.from_user.first_name
    
    if not is_user_joined_all(message.from_user.id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(config['channels'], 1):
            markup.add(types.InlineKeyboardButton(f"📢 Join Channel {i}", url=ch['link']))
        markup.add(types.InlineKeyboardButton("✅ Verify Join", callback_data="verify_join"))
        bot.send_message(message.chat.id, "✨ **সার্ভিসটি ব্যবহার করতে নিচের চ্যানেলে জয়েন করুন।**", reply_markup=markup, parse_mode="Markdown")
        return

    u_data, is_new = get_user(message.from_user.id, name)

    args = message.text.split()
    if len(args) > 1 and is_new:
        ref_id = args[1]
        if ref_id in users and ref_id != uid:
            users[ref_id]['balance'] += config['ref_bonus']
            users[ref_id]['ref_count'] += 1
            save_data(USER_FILE, users)
            try: bot.send_message(ref_id, f"🎊 Referral Bonus Earned! {config['ref_bonus']} BDT")
            except: pass

    if is_new:
        welcome_text = (
            f"👑 **Welcome , {name}!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌟 **Premium OTP & SMS Hub**-এ আপনাকে স্বাগতম।\n\n"
            f"🚀 **আমাদের বিশেষত্ব:**\n"
            f"⚡️ আল্ট্রা-ফাস্ট ওটিপি ডেলিভারি সিস্টেম।\n"
            f"🌍 বিশ্বের ১০০+ দেশের নাম্বার ।\n"
            f"🛡 ১০০% নিরাপদ এবং প্রাইভেট ট্রানজেকশন।\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_keyboard(), parse_mode="Markdown")
    else:
        send_country_list(message.chat.id)

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
    text = (f"🛠 **Admin Control Panel**\n\n💰 Refer Bonus: {config['ref_bonus']} BDT\n🏧 Min Withdraw: {config['min_withdraw']} BDT")
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['text', 'document'])
def handle_all(message):
    if not is_user_joined_all(message.from_user.id): return
    uid = str(message.from_user.id)
    u_data, _ = get_user(uid)

    if message.text == "📞 Get Number":
        send_country_list(message.chat.id)
    elif message.text == "💰 Balance":
        bot.send_message(message.chat.id, f"💳 **Balance:** {u_data['balance']} BDT", parse_mode="Markdown")
    elif message.text == "🎁 Refer & Earn":
        bot_user = (bot.get_me()).username
        bot.send_message(message.chat.id, f"🎁 **Referral:**\n🔗 https://t.me/{bot_user}?start={uid}", parse_mode="Markdown")
    elif message.text == "💸 Withdraw":
        bot.send_message(message.chat.id, f"❌ **Min Withdraw:** {config['min_withdraw']} BDT", parse_mode="Markdown")
    elif message.text == "🌍 Available Countries":
        current_db = load_data(DB_FILE, {})
        active = [f"✅ {k} ({len(v)})" for k, v in current_db.items() if v and len(v) > 0]
        bot.send_message(message.chat.id, "🌍 **Stock List:**\n\n" + "\n".join(active) if active else "❌ Empty", parse_mode="Markdown")
    
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
                c = detect_country(r); n = f"+{r.lstrip('+')}"
                if c not in curr_db: curr_db[c] = []
                if n not in curr_db[c]: curr_db[c].append(n); added += 1
            save_data(DB_FILE, curr_db)
            bot.reply_to(message, f"✅ Added {added} numbers.")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = str(call.from_user.id)
    if call.data == "verify_join":
        if is_user_joined_all(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            handle_start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ জয়েন করেননি!", show_alert=True)
    elif call.data == "back_c":
        bot.answer_callback_query(call.id)
        send_country_list(call.message.chat.id, call.message.message_id)
    elif call.data == "conf_ref":
        msg = bot.send_message(call.message.chat.id, "Enter Refer Bonus Amount:")
        bot.register_next_step_handler(msg, lambda m: update_conf(m, 'ref_bonus'))
    elif call.data == "conf_with":
        msg = bot.send_message(call.message.chat.id, "Enter Min Withdraw Amount:")
        bot.register_next_step_handler(msg, lambda m: update_conf(m, 'min_withdraw'))
    elif call.data == "conf_bc":
        msg = bot.send_message(call.message.chat.id, "📢 Send Broadcast Message:")
        bot.register_next_step_handler(msg, do_broadcast)
    elif call.data == "conf_chan":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("➕ Add Channel", callback_data="add_ch"))
        for i, ch in enumerate(config['channels']):
            markup.add(types.InlineKeyboardButton(f"🗑️ Delete {ch['username']}", callback_data=f"delch_{i}"))
        bot.edit_message_text("⚙️ Manage Channels:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif call.data == "conf_clear":
        curr_db = load_data(DB_FILE, {})
        markup = types.InlineKeyboardMarkup()
        for k, v in curr_db.items():
            if v: markup.add(types.InlineKeyboardButton(f"🗑️ {k} ({len(v)})", callback_data=f"rmv_{k}"))
        bot.edit_message_text("🗑️ Select country to clear stock:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif call.data.startswith('rmv_'):
        c = call.data.replace('rmv_', ''); curr_db = load_data(DB_FILE, {}); curr_db[c] = []
        save_data(DB_FILE, curr_db); bot.answer_callback_query(call.id, f"✅ {c} Cleared!"); admin_settings(call.message)
    elif call.data == "add_ch":
        msg = bot.send_message(call.message.chat.id, "Send Channel `@Username Link`:")
        bot.register_next_step_handler(msg, process_add_ch)
    elif call.data == "delch_":
        idx = int(call.data.split("_")[1])
        config['channels'].pop(idx)
        save_data(CONFIG_FILE, config)
        bot.answer_callback_query(call.id, "✅ Deleted!")
        admin_settings(call.message)
    elif call.data.startswith('sel_'):
        country = call.data.replace('sel_', '')
        curr_db = load_data(DB_FILE, {})
        if country in curr_db and curr_db[country]:
            num = str(curr_db[country].pop(0))
            save_data(DB_FILE, curr_db)
            try:
                p = phonenumbers.parse(num)
                m_key = f"{p.country_code}_{num[-3:]}"
                o_db = load_data(ORDERS_FILE, {})
                if m_key not in o_db: o_db[m_key] = []
                o_db[m_key].append(uid); save_data(ORDERS_FILE, o_db)
            except: pass

            markup = types.InlineKeyboardMarkup(row_width=1)
            try: markup.add(types.InlineKeyboardButton(text=f"📱 {num}", copy_text=num))
            except: markup.add(types.InlineKeyboardButton(text=f"📱 {num}", callback_data="none"))
            markup.add(
                types.InlineKeyboardButton("🔄 CHANGE NUMBER", callback_data=f"sel_{country}"),
                types.InlineKeyboardButton("🌐 CHANGE COUNTRY", callback_data="back_c"),
                types.InlineKeyboardButton("🚀 GET OTP", url=OTP_GROUP_LINK)
            )
            msg_text = f"🎁 Number for: {country}\n\nNumber: {num}\n\n💡 বাটনে ক্লিক করে নাম্বারটি কপি করুন।"
            try: bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
            except: bot.send_message(call.message.chat.id, msg_text, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ স্টক শেষ!", show_alert=True)

def process_add_ch(message):
    try:
        parts = message.text.split()
        config['channels'].append({"username": parts[0], "link": parts[1]})
        save_data(CONFIG_FILE, config); bot.send_message(message.chat.id, "✅ Channel Added!")
    except: bot.send_message(message.chat.id, "❌ Error. Use: `@User https://link`")

def update_conf(message, key):
    try:
        config[key] = float(message.text); save_data(CONFIG_FILE, config); bot.send_message(message.chat.id, "✅ Updated Successfully!")
    except: bot.send_message(message.chat.id, "❌ Invalid Input.")

def do_broadcast(message):
    u_list = load_data(USER_FILE, {})
    success = 0
    for uid in u_list.keys():
        try: bot.send_message(uid, message.text); time.sleep(0.05); success += 1
        except: continue
    bot.send_message(message.chat.id, f"✅ Done! Sent to {success} users.")

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
        except: pass
    else:
        bot.send_message(chat_id, txt, reply_markup=markup, parse_mode="Markdown")

if __name__ == "__main__":
    bot.infinity_polling()
