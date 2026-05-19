import telebot
from telebot import types
import re
import json
import os
import time
import threading
import phonenumbers
from phonenumbers import geocoder

# --- CONFIGURATION ---
API_TOKEN = '7634786660:AAHvY09ndmYnO6pLpz_84rSLqGUEMlfwNd4'
ADMIN_ID = 6781949890
DB_FILE = 'numbers_db.json'
USER_FILE = 'Users_data.json'  # ফাইল নেম ঠিক করা হয়েছে
CONFIG_FILE = 'settings.json'
OTP_GROUP_LINK = "https://t.me/Premium_OTP_chat"

bot = telebot.TeleBot(API_TOKEN, threaded=True, num_threads=10)

ADMIN_UPLOAD_TEMP = {}

SERVICES = {
    "FACEBOOK": {"name": "Facebook", "icon": "🔵"},
    "WHATSAPP": {"name": "WhatsApp", "icon": "🟢"},
    "TELEGRAM": {"name": "Telegram", "icon": "✈️"}
}

def load_data(file, default):
    if os.path.exists(file):
        try:
            if os.path.getsize(file) == 0: return default
            with open(file, 'r', encoding='utf-8') as f: return json.load(f)
        except: return default
    return default

def save_data(file, data):
    try:
        with open(file, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
    except: pass

config = load_data(CONFIG_FILE, {"ref_bonus": 2.0, "min_withdraw": 500.0, "channels": []})

def is_user_joined_all(user_id):
    if not config.get('channels'): return True
    for ch in config['channels']:
        try:
            member = bot.get_chat_member(ch['username'], user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

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

def send_service_list(chat_id, message_id=None):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, val in SERVICES.items():
        markup.add(types.InlineKeyboardButton(f"{val['icon']} {val['name']}", callback_data=f"show_srv_{key}"))
    
    txt = "⚔️ <b>Select a Service:</b>"
    if message_id:
        try: bot.edit_message_text(txt, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
        except: pass
    else:
        bot.send_message(chat_id, txt, reply_markup=markup, parse_mode="HTML")

def send_country_list(chat_id, service_key, message_id=None):
    curr_db = load_data(DB_FILE, {})
    srv_stock = curr_db.get(service_key, {})
    active = {k: v for k, v in srv_stock.items() if isinstance(v, list) and len(v) > 0}
    
    if not active:
        txt = f"❌ <b>Out of stock for {SERVICES[service_key]['name']}!</b>"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back To Services", callback_data="back_to_services"))
        if message_id: bot.edit_message_text(txt, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
        else: bot.send_message(chat_id, txt, reply_markup=markup, parse_mode="HTML")
        return
        
    markup = types.InlineKeyboardMarkup(row_width=1)
    for c in sorted(active.keys()):
        markup.add(types.InlineKeyboardButton(f"{c} ({len(active[c])})", callback_data=f"sel_{service_key}_{c}"))
    markup.add(types.InlineKeyboardButton("⬅️ Back To Services", callback_data="back_to_services"))
    
    txt = f"📍 <b>Select Country for {SERVICES[service_key]['name']}:</b>"
    try:
        if message_id: bot.edit_message_text(txt, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
        else: bot.send_message(chat_id, txt, reply_markup=markup, parse_mode="HTML")
    except: pass

# 🔥 ব্রডকাস্ট ইঞ্জিন ঠিক করা হয়েছে
def async_stock_alert_broadcast(alert_msg):
    users_data = load_data(USER_FILE, {})
    if not users_data: return
    
    for uid in users_data.keys():
        try:
            bot.send_message(chat_id=int(uid), text=alert_msg, parse_mode="HTML")
            time.sleep(0.1)
        except Exception:
            continue

@bot.message_handler(commands=['start'])
def handle_start(message):
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
        f"✨ **Welcome to PREMIUM SMS PANEL**\n"
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
        types.InlineKeyboardButton("📊 Export Available Stock", callback_data="conf_export"),
        types.InlineKeyboardButton("🗑️ Clear Stock", callback_data="conf_clear"),
        types.InlineKeyboardButton("📢 Broadcast Message", callback_data="conf_bc")
    )
    text = (f"🛠 **Admin Control Panel**\n\n💰 Refer Bonus: {config['ref_bonus']} BDT\n🏧 Min Withdraw: {config['min_withdraw']} BDT")
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(content_types=['text', 'document'])
def handle_all(message):
    uid = str(message.from_user.id)
    if not is_user_joined_all(message.from_user.id): return
    
    if message.text == "📞 Get Number":
        send_service_list(message.chat.id)
    elif message.text == "💰 Balance":
        users = load_data(USER_FILE, {})
        u_data = users.get(uid, {"balance": 0.0})
        bot.send_message(message.chat.id, f"💳 **Current Balance:** {u_data.get('balance', 0.0)} BDT")
    elif message.text == "🎁 Refer & Earn":
        bot_user = (bot.get_me()).username
        bot.send_message(message.chat.id, f"🎁 **Refer Link:** https://t.me/{bot_user}?start={uid}")
    elif message.text == "💸 Withdraw":
        bot.send_message(message.chat.id, f"❌ **Min Withdraw:** {config['min_withdraw']} BDT")
    elif message.text == "🌍 Available Countries":
        current_db = load_data(DB_FILE, {})
        summary_lines = []
        for s_key, s_val in SERVICES.items():
            srv_stock = current_db.get(s_key, {})
            active_cnt = [f"{k} ({len(v)})" for k, v in srv_stock.items() if v and len(v) > 0]
            if active_cnt:
                summary_lines.append(f"{s_val['icon']} <b>{s_val['name']} Stock:</b>")
                for line in active_cnt:
                    summary_lines.append(f"  └─ ✅ {line}")
        bot.send_message(message.chat.id, "\n".join(summary_lines) if summary_lines else "❌ Empty", parse_mode="HTML")
    
    elif int(message.from_user.id) == ADMIN_ID:
        txt = message.text if message.text else ""
        if message.content_type == 'document':
            f_info = bot.get_file(message.document.file_id)
            txt = bot.download_file(f_info.file_path).decode('utf-8')
        
        found = re.findall(r'\+?\d{9,15}', txt)
        if found:
            ADMIN_UPLOAD_TEMP[message.from_user.id] = found
            markup = types.InlineKeyboardMarkup(row_width=1)
            for s_key, s_val in SERVICES.items():
                markup.add(types.InlineKeyboardButton(f"Add to {s_val['name']}", callback_data=f"addstock_{s_key}"))
            markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="addstock_CANCEL"))
            bot.reply_to(message, f"🎯 <b>{len(found)} numbers detected.</b>\nSelect the target service to load this stock:", reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    try: bot.answer_callback_query(call.id)
    except: pass

    chat_id = call.message.chat.id
    message_id = call.message.message_id
    uid = str(call.from_user.id)

    if call.data == "verify_join":
        if is_user_joined_all(call.from_user.id):
            bot.delete_message(chat_id, message_id)
            handle_start(call.message)
        else: bot.answer_callback_query(call.id, "❌ জয়েন করেননি!", show_alert=True)

    elif call.data == "back_to_services":
        send_service_list(chat_id, message_id)

    elif call.data.startswith('show_srv_'):
        service_key = call.data.replace('show_srv_', '')
        send_country_list(chat_id, service_key, message_id)

    elif call.data.startswith('addstock_'):
        srv_target = call.data.replace('addstock_', '')
        admin_id = call.from_user.id
        
        if srv_target == "CANCEL":
            if admin_id in ADMIN_UPLOAD_TEMP: del ADMIN_UPLOAD_TEMP[admin_id]
            bot.edit_message_text("❌ Upload Session Cancelled.", chat_id, message_id)
            return
            
        if admin_id not in ADMIN_UPLOAD_TEMP: return
            
        found_numbers = ADMIN_UPLOAD_TEMP[admin_id]
        curr_db = load_data(DB_FILE, {})
        
        if srv_target not in curr_db: 
            curr_db[srv_target] = {}
            
        added = 0
        added_countries = set()
        
        for r in found_numbers:
            clean_r = "+" + r.lstrip('+')
            flag = detect_country_flag(clean_r)
            try: name = geocoder.description_for_number(phonenumbers.parse(clean_r), "en")
            except: name = "Unknown"
            c_name = f"{flag} {name}" if name != "Unknown" else f"📍 Zone +{clean_r[1:4]}"
            
            if c_name not in curr_db[srv_target]: 
                curr_db[srv_target][c_name] = []
                
            if clean_r not in curr_db[srv_target][c_name]:
                curr_db[srv_target][c_name].append(clean_r)
                added_countries.add(c_name)
                added += 1
                
        save_data(DB_FILE, curr_db)
        del ADMIN_UPLOAD_TEMP[admin_id]
        
        if added > 0:
            bot.edit_message_text(f"✅ Successfully loaded {added} unique numbers to {SERVICES[srv_target]['name']}.", chat_id, message_id)
            
            countries_list_str = ", ".join(sorted(added_countries))
            
            alert_msg = (
                f"📢 <b>New Fresh Stock Added!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🛠 <b>Service:</b> {SERVICES[srv_target]['icon']} {SERVICES[srv_target]['name']}\n"
                f"🌍 <b>Countries Added:</b> {countries_list_str}\n"
                f"⚡ <b>Status:</b> High Traffic Live Now 🔥\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <i>সবাই দ্রুত কাজ শুরু করুন এবং ওটিপি সাবমিট করুন!</i>"
            )
            # অটো ব্রডকাস্ট এখানে ট্রিগার হবে
            threading.Thread(target=async_stock_alert_broadcast, args=(alert_msg,), daemon=True).start()
        else:
            bot.edit_message_text("⚠️ No new or unique numbers were added.", chat_id, message_id)

    elif call.data.startswith('sel_'):
        data_string = call.data.replace('sel_', '')
        parts = data_string.split('_', 1)
        
        if len(parts) < 2: return
        service_key = parts[0]
        country = parts[1]
        
        curr_db = load_data(DB_FILE, {})
        srv_stock = curr_db.get(service_key, {}).get(country, [])
        
        if len(srv_stock) < 1:
            bot.send_message(chat_id, "❌ এই দেশের স্টক শেষ হয়ে গেছে!")
            return
            
        users = load_data(USER_FILE, {})
        if uid not in users: 
            users[uid] = {"balance": 0.0, "ref_count": 0, "name": call.from_user.first_name, "joined": True, "active_numbers": []}
        
        users[uid]["active_numbers"] = []
        delivered_numbers = []
        take_count = min(3, len(srv_stock))
        
        for _ in range(take_count):
            if srv_stock:
                raw_num = str(srv_stock.pop(0))
                delivered_numbers.append(raw_num)
                users[uid]["active_numbers"].append({"number": raw_num, "country": country})
        
        curr_db[service_key][country] = srv_stock
        save_data(DB_FILE, curr_db)
        save_data(USER_FILE, users)
        
        if not delivered_numbers: return

        raw_keyboard = []
        flag_icon = country.split()[0] if country.split() else "🌍"
        
        for num in delivered_numbers:
            btn_text = f"{flag_icon} {num}"
            number_button = {
                "text": btn_text,
                "copy_text": {"text": str(num)}
            }
            raw_keyboard.append([number_button])
            
        raw_keyboard.append([{"text": "🔄 CHANGE NUMBERS", "callback_data": f"show_srv_{service_key}"}])
        raw_keyboard.append([{"text": "🌐 CHANGE COUNTRY", "callback_data": f"show_srv_{service_key}"}])
        raw_keyboard.append([{"text": "🚀 GET OTP", "url": OTP_GROUP_LINK}])
        
        custom_markup = {"inline_keyboard": raw_keyboard}
        msg_text = f"🌍 **Country:** {country}\n⚙️ **Service:** {SERVICES[service_key]['icon']} {SERVICES[service_key]['name']}\n━━━━━━━━━━━━━━\n⏳ **Waiting for OTP...**"
        
        try:
            bot.edit_message_text(
                text=msg_text, 
                chat_id=chat_id, 
                message_id=message_id, 
                reply_markup=json.dumps(custom_markup), 
                parse_mode="Markdown"
            )
        except: pass

    elif call.data == "conf_bc":
        msg = bot.send_message(chat_id, "Enter Broadcast Message:")
        bot.register_next_step_handler(msg, do_broadcast)
    
    # অন্যান্য কন্ট্রোল প্যানেল কমান্ডগুলো এখানে থাকবে...
    elif call.data == "back_settings":
        admin_settings(call.message)

def do_broadcast(message):
    threading.Thread(target=async_stock_alert_broadcast, args=(message.text,), daemon=True).start()
    bot.send_message(message.chat.id, "📢 Broadcast started successfully in background!")

def main():
    try: bot.remove_webhook()
    except: pass
    bot.infinity_polling(none_stop=True, timeout=60, long_polling_timeout=30)

if __name__ == "__main__":
    main()
