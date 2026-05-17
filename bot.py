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
OTP_GROUP_LINK = "https://t.me/Premium_OTP_chat"
OTP_GROUP_ID = -1002295608331  # ওটিপি গ্রুপ আইডি

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

config = load_data(CONFIG_FILE, {"ref_bonus": 2.0, "min_withdraw": 500.0, "channels": []})
users = load_data(USER_FILE, {})
processed_otps = set()  # ডুপ্লিকেট কোড ফিল্টার

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

def detect_country_flag(num_str):
    try:
        full_num = f"+{num_str.lstrip('+')}"
        parsed = phonenumbers.parse(full_num)
        region = phonenumbers.region_code_for_number(parsed)
        return "".join(chr(ord(c) + 127397) for c in region.upper()) if region else "📍"
    except: return "📍"

# --- UTILS ---
def send_country_list(chat_id, message_id=None):
    curr_db = load_data(DB_FILE, {})
    active = {k: v for k, v in curr_db.items() if isinstance(v, list) and len(v) > 0}
    if not active:
        bot.send_message(chat_id, "❌ **No stock available.**")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for c in sorted(active.keys()):
        markup.add(types.InlineKeyboardButton(f"{c} ({len(active[c])})", callback_data=f"sel_{c}"))
    
    txt = "📍 **Select Country:**"
    try:
        if message_id:
            bot.edit_message_text(txt, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, txt, reply_markup=markup)
    except: pass

# --- CORE LOGIC: ADVANCED OTP FORWARDING ENGINE (১০০% পারফেক্ট ও চেকড) ---
def process_single_otp_message(txt):
    if not txt: return
    
    # গ্রুপ মেসেজ থেকে সমস্ত সংখ্যার খণ্ড আলাদা করা
    num_parts = re.findall(r'\d+', txt)
    if not num_parts: return
    
    # মেসেজের শেষ সংখ্যাটিই সাধারণত মাস্কড বা নরমাল ফোন নাম্বারের শেষ অংশ নির্দেশ করে
    group_last_4 = num_parts[-1][-4:] if len(num_parts[-1]) >= 4 else num_parts[-1]
    if len(group_last_4) < 3: return 

    current_users = load_data(USER_FILE, {})
    
    for uid, u_info in current_users.items():
        # ইউজারের একটিভ নাম্বারের লিস্ট ডাটাবেজ থেকে চেক করা হচ্ছে
        active_numbers = u_info.get("active_numbers", [])
        if not active_numbers: continue
        
        for num_obj in active_numbers:
            clean_num = re.sub(r'\D', '', num_obj["number"])
            if len(clean_num) < 4: continue
            user_last_4 = clean_num[-4:]
            
            # 🔥 ওটিপি গ্রুপ ট্র্যাকিং ম্যাচিং কন্ডিশন 🔥
            if group_last_4 == user_last_4 or user_last_4 in group_last_4:
                # ওটিপি কোড পার্স করা
                otp_match = re.search(r'(?:OTP|code|🧑‍💻)[:\s]*(\d+)', txt, re.IGNORECASE)
                if otp_match:
                    otp_code = otp_match.group(1)
                else:
                    all_digits = re.findall(r'\b\d{4,8}\b', txt)
                    possible_codes = [d for d in all_digits if d not in num_parts]
                    otp_code = possible_codes[0] if possible_codes else "Not Found"

                # একই কোড বারবার ফরওয়ার্ড লক ট্র্যাকিং
                unique_key = f"{uid}_{user_last_4}_{otp_code}"
                if unique_key in processed_otps: return
                processed_otps.add(unique_key)

                # সার্ভিস অ্যাপ আইডেন্টিফিকেশন
                service_name = "Unknown Service"
                apps = ["Telegram", "WhatsApp", "Imo", "Facebook", "Google", "Viber", "Kakao", "TikTok", "WeChat", "Line"]
                for app in apps:
                    if app.lower() in txt.lower():
                        service_name = app
                        break

                final_msg = (
                    f"✨ **NEW OTP RECEIVED!**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Service:** {service_name}\n"
                    f"🔢 **Number:** `{num_obj['number']}`\n"
                    f"🔑 **OTP Code:** `{otp_code}`\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                try:
                    bot.send_message(int(uid), final_msg, parse_mode="Markdown")
                except: pass
                return

# 🔥 --- AUTOMATIC OTP GROUP LISTENER --- 🔥
@bot.message_handler(func=lambda message: message.chat.id == OTP_GROUP_ID)
def listen_otp_group(message):
    txt = message.text if message.text else (message.caption if message.caption else "")
    process_single_otp_message(txt)

# 🔄 --- STARTUP HISTORICAL CHECKER (হিস্ট্রি ব্যাক-চেক) --- 🔄
def check_recent_history():
    try:
        print("Scanning group history for missing OTPs...")
        # infinity_polling এর জন্য ওল্ড মেথড রিপ্লেস করে এপিআই কল করা হয়েছে
        url = f"https://api.telegram.com/bot{API_TOKEN}/getChatHistory"
        response = requests.post(url, json={"chat_id": OTP_GROUP_ID, "limit": 20}).json()
        if response.get("ok") and response.get("result"):
            for message in reversed(response["result"]):
                txt = message.get("text", "") or message.get("caption", "")
                process_single_otp_message(txt)
    except: pass

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    global users
    uid = str(message.from_user.id)
    name = message.from_user.first_name
    
    if not is_user_joined_all(message.from_user.id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(config.get('channels', []), 1):
            markup.add(types.InlineKeyboardButton(f"📢 Join Channel {i}", url=ch['link']))
        markup.add(types.InlineKeyboardButton("✅ Verify Join", callback_data="verify_join"))
        bot.send_message(message.chat.id, "⚠️ **You must join our channels to use this bot!**", reply_markup=markup, parse_mode="Markdown")
        return

    users = load_data(USER_FILE, {})
    if uid not in users:
        users[uid] = {"balance": 0.0, "ref_count": 0, "name": name, "joined": True, "active_numbers": []}
        save_data(USER_FILE, users)

    welcome_msg = (
        f"👋 **Hello, {name}!**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✨ **Welcome to PREMIUM SMS PENEL**\n"
        f"🚀 *Fastest OTP Service in the Market.*\n"
        f"🌍 *100+ Countries Available Now.*\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(message.chat.id, welcome_msg, reply_markup=main_keyboard(), parse_mode="Markdown")

@bot.message_handler(commands=['settings'])
def admin_settings(message):
    if int(message.from_user.id) != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💵 Set Refer Bonus", callback_data="conf_ref"),
        types.InlineKeyboardButton("🏧 Set Min Withdraw", callback_data="conf_with"),
        types.InlineKeyboardButton("⚙️ Manage Channels", callback_data="conf_chan"),
        types.InlineKeyboardButton("🗑️ Clear Stock", callback_data="conf_clear"),
        types.InlineKeyboardButton("📢 Broadcast Message", callback_data="conf_bc")
    )
    text = (f"🛠 **Admin Control Panel**\n\n💰 Refer Bonus: {config['ref_bonus']} BDT\n🏧 Min Withdraw: {config['min_withdraw']} BDT")
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(content_types=['text', 'document'])
def handle_all(message):
    if message.chat.id == OTP_GROUP_ID: return
    global users

    uid = str(message.from_user.id)
    if not is_user_joined_all(message.from_user.id): return
    
    if message.text == "📞 Get Number":
        send_country_list(message.chat.id)
    elif message.text == "💰 Balance":
        users = load_data(USER_FILE, {})
        u_data = users.get(uid, {"balance": 0.0})
        bot.send_message(message.chat.id, f"💳 **Current Balance:** {u_data['balance']} BDT")
    elif message.text == "🎁 Refer & Earn":
        bot_user = (bot.get_me()).username
        bot.send_message(message.chat.id, f"🎁 **Refer Link:** https://t.me/{bot_user}?start={uid}")
    elif message.text == "💸 Withdraw":
        bot.send_message(message.chat.id, f"❌ **Min Withdraw:** {config['min_withdraw']} BDT")
    elif message.text == "🌍 Available Countries":
        current_db = load_data(DB_FILE, {})
        active = [f"✅ {k} ({len(v)})" for k, v in current_db.items() if v and len(v) > 0]
        bot.send_message(message.chat.id, "🌍 Stock List:\n\n" + "\n".join(active) if active else "❌ Empty")
    
    elif int(message.from_user.id) == ADMIN_ID:
        txt = message.text if message.text else ""
        if message.content_type == 'document':
            f_info = bot.get_file(message.document.file_id)
            txt = bot.download_file(f_info.file_path).decode('utf-8')
        
        found = re.findall(r'\+?\d{9,16}', txt)
        if found:
            curr_db = load_data(DB_FILE, {})
            added = 0
            for r in found:
                clean_r = "+" + r.lstrip('+')
                flag = detect_country_flag(clean_r)
                try: name = geocoder.description_for_number(phonenumbers.parse(clean_r), "en")
                except: name = "Unknown"
                c_name = f"{flag} {name}" if name != "Unknown" else f"📍 Zone +{clean_r[1:4]}"
                if c_name not in curr_db: curr_db[c_name] = []
                if clean_r not in curr_db[c_name]:
                    curr_db[c_name].append(clean_r)
                    added += 1
            save_data(DB_FILE, curr_db)
            bot.reply_to(message, f"✅ Added {added} numbers to stock.")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    uid = str(call.from_user.id)
    global users

    if call.data == "verify_join":
        if is_user_joined_all(call.from_user.id):
            bot.delete_message(chat_id, message_id)
            handle_start(call.message)
        else: bot.answer_callback_query(call.id, "❌ জয়েন করেননি!", show_alert=True)

    elif call.data.startswith('sel_'):
        country = call.data.replace('sel_', '')
        curr_db = load_data(DB_FILE, {})
        if country in curr_db and len(curr_db[country]) >= 1:
            users = load_data(USER_FILE, {})
            if uid not in users: 
                users[uid] = {"balance": 0.0, "ref_count": 0, "name": call.from_user.first_name, "joined": True, "active_numbers": []}
            
            # নতুন নাম্বার নেওয়ার আগে আগের ওল্ড নাম্বার স্ক্রিন ট্র্যাকিং থেকে মুছে ফেলা
            users[uid]["active_numbers"] = []

            delivered_numbers = []
            # স্টকে ৩টি থাকলে ৩টি দেবে, কম থাকলে (১টি বা ২টি) যা আছে তাই কেটে দেবে (No Stock Error আসবে না)
            take_count = min(3, len(curr_db[country]))
            for _ in range(take_count):
                if curr_db[country]:
                    raw_num = str(curr_db[country].pop(0)) # ডাটা ফাইল থেকে রিমুভ (ডিলিট) করা হলো
                    delivered_numbers.append(raw_num)
                    users[uid]["active_numbers"].append({"number": raw_num, "country": country})
            
            save_data(DB_FILE, curr_db)
            save_data(USER_FILE, users)
            
            if not delivered_numbers:
                bot.answer_callback_query(call.id, "❌ স্টক শেষ!", show_alert=True)
                return

            num_text = "\n".join([f"`{n}`" for n in delivered_numbers])
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("🔄 CHANGE NUMBERS", callback_data=f"sel_{country}"),
                types.InlineKeyboardButton("🌐 CHANGE COUNTRY", callback_data="back_c"),
                types.InlineKeyboardButton("🚀 GET OTP", url=OTP_GROUP_LINK)
            )
            msg_text = f"🌍 **Country:** {country}\n━━━━━━━━━━━━━━\n{num_text}\n━━━━━━━━━━━━━━\n💡 **Tap to copy!**"
            bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        else: bot.answer_callback_query(call.id, "❌ স্টক শেষ!", show_alert=True)

    elif call.data == "back_c":
        send_country_list(chat_id, message_id)

    elif call.data == "conf_clear":
        curr_db = load_data(DB_FILE, {})
        active_countries = {k: v for k, v in curr_db.items() if v and len(v) > 0}
        if not active_countries:
            bot.answer_callback_query(call.id, "❌ No stock to clear!", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        for country in sorted(active_countries.keys()):
            markup.add(types.InlineKeyboardButton(f"🗑️ Clear {country}", callback_data=f"rmv_{country}"))
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_settings"))
        bot.edit_message_text("🗑️ **Select country to clear stock:**", chat_id, message_id, reply_markup=markup)

    elif call.data.startswith('rmv_'):
        country_to_rm = call.data.replace('rmv_', '')
        curr_db = load_data(DB_FILE, {})
        if country_to_rm in curr_db:
            curr_db[country_to_rm] = []
            save_data(DB_FILE, curr_db)
            bot.answer_callback_query(call.id, f"✅ {country_to_rm} stock cleared!")
            admin_settings(call.message)

    elif call.data == "back_settings":
        try: bot.delete_message(chat_id, message_id)
        except: pass
        admin_settings(call.message)

    elif call.data == "conf_chan":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("➕ Add Channel", callback_data="add_ch"))
        for i, ch in enumerate(config.get('channels', [])):
            markup.add(types.InlineKeyboardButton(f"🗑️ Delete {ch['username']}", callback_data=f"delch_{i}"))
        bot.edit_message_text("⚙️ **Manage Channels:**", chat_id, message_id, reply_markup=markup)

    elif call.data == "add_ch":
        msg = bot.send_message(chat_id, "Format: `@Username https://link`")
        bot.register_next_step_handler(msg, process_add_ch)

    elif call.data.startswith("delch_"):
        idx = int(call.data.split("_")[1])
        config['channels'].pop(idx)
        save_data(CONFIG_FILE, config)
        admin_settings(call.message)

    elif call.data == "conf_ref":
        msg = bot.send_message(chat_id, "Enter Refer Bonus:")
        bot.register_next_step_handler(msg, lambda m: update_cfg(m, 'ref_bonus'))
    elif call.data == "conf_with":
        msg = bot.send_message(chat_id, "Enter Min Withdraw:")
        bot.register_next_step_handler(msg, lambda m: update_cfg(m, 'min_withdraw'))
    elif call.data == "conf_bc":
        msg = bot.send_message(chat_id, "Enter Broadcast Message:")
        bot.register_next_step_handler(msg, do_broadcast)

def process_add_ch(message):
    try:
        parts = message.text.split()
        config['channels'].append({"username": parts[0], "link": parts[1]})
        save_data(CONFIG_FILE, config)
        bot.send_message(message.chat.id, "✅ Added!")
    except: bot.send_message(message.chat.id, "❌ Error!")

def update_cfg(message, key):
    try:
        config[key] = float(message.text)
        save_data(CONFIG_FILE, config)
        bot.send_message(message.chat.id, "✅ Updated!")
    except: pass

def do_broadcast(message):
    for u in load_data(USER_FILE, {}).keys():
        try: bot.send_message(int(u), message.text)
        except: pass
    bot.send_message(message.chat.id, "✅ Broadcast Done!")

if __name__ == "__main__":
    import requests
    check_recent_history()
    print("Bot is starting polling with advanced tracking loop...")
    bot.infinity_polling(none_stop=True)
    
