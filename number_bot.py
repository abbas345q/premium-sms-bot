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
    welcome_msg = f"👋 **Hello, {name}!**\n✨ **Welcome to PREMIUM SMS PANEL**"
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
        types.InlineKeyboardButton("🗑️ Clear Stock", callback_data="conf_clear")
    )
    bot.send_message(message.chat.id, "🛠 **Admin Control Panel**", reply_markup=markup)

@bot.message_handler(content_types=['text', 'document'])
def handle_all(message):
    if not is_user_joined_all(message.from_user.id): return
    if message.text == "📞 Get Number": send_service_list(message.chat.id)
    elif message.text == "💰 Balance":
        users = load_data(USER_FILE, {})
        u_data = users.get(str(message.from_user.id), {"balance": 0.0})
        bot.send_message(message.chat.id, f"💳 **Current Balance:** {u_data.get('balance', 0.0)} BDT")
    elif int(message.from_user.id) == ADMIN_ID and message.content_type == 'document':
        f_info = bot.get_file(message.document.file_id)
        txt = bot.download_file(f_info.file_path).decode('utf-8')
        found = re.findall(r'\+?\d{9,15}', txt)
        if found:
            ADMIN_UPLOAD_TEMP[message.from_user.id] = found
            markup = types.InlineKeyboardMarkup(row_width=1)
            for s_key, s_val in SERVICES.items():
                markup.add(types.InlineKeyboardButton(f"Add to {s_val['name']}", callback_data=f"addstock_{s_key}"))
            bot.reply_to(message, "🎯 Select target service:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    # বাটন দ্রুত রেসপন্সের জন্য
    bot.answer_callback_query(call.id)
    chat_id, message_id = call.message.chat.id, call.message.message_id
    
    if call.data == "conf_export":
        markup = types.InlineKeyboardMarkup(row_width=1)
        for key, val in SERVICES.items():
            markup.add(types.InlineKeyboardButton(f"📥 Export {val['name']}", callback_data=f"export_{key}"))
        bot.edit_message_text("📊 <b>Select service to export:</b>", chat_id, message_id, reply_markup=markup, parse_mode="HTML")
        
    elif call.data.startswith('export_'):
        srv = call.data.replace('export_', '')
        curr_db = load_data(DB_FILE, {})
        srv_stock = curr_db.get(srv, {})
        
        all_nums = []
        for country, nums in srv_stock.items():
            all_nums.extend(nums)
            
        if not all_nums:
            bot.answer_callback_query(call.id, "❌ Empty Stock!")
            return
            
        file_name = f"{srv}_stock.txt"
        with open(file_name, 'w') as f:
            f.write("\n".join(all_nums))
        
        with open(file_name, 'rb') as f:
            bot.send_document(chat_id, f)
        os.remove(file_name)
    
    elif call.data.startswith('show_srv_'): send_country_list(chat_id, call.data.replace('show_srv_', ''), message_id)
    elif call.data == "back_to_services": send_service_list(chat_id, message_id)
    
    elif call.data.startswith('addstock_'):
        srv_target = call.data.replace('addstock_', '')
        found_numbers = ADMIN_UPLOAD_TEMP.get(call.from_user.id, [])
        curr_db = load_data(DB_FILE, {})
        if srv_target not in curr_db: curr_db[srv_target] = {}
        
        added_report = {}
        total_added = 0
        for r in found_numbers:
            clean_r = "+" + r.lstrip('+')
            flag = detect_country_flag(clean_r)
            try: name = geocoder.description_for_number(phonenumbers.parse(clean_r), "en")
            except: name = "Unknown"
            c_name = f"{flag} {name}" if name != "Unknown" else f"📍 Zone +{clean_r[1:4]}"
            
            if c_name not in curr_db[srv_target]: curr_db[srv_target][c_name] = []
            if clean_r not in curr_db[srv_target][c_name]:
                curr_db[srv_target][c_name].append(clean_r)
                added_report[c_name] = added_report.get(c_name, 0) + 1
                total_added += 1
                
        save_data(DB_FILE, curr_db)
        report = f"✅ <b>Stock Updated!</b>\n🛠 <b>Service:</b> {SERVICES[srv_target]['name']}\n🔢 <b>Total:</b> {total_added}\n\n"
        for country, count in added_report.items():
            report += f"{country}: <b>{count}</b>\n"
        bot.edit_message_text(report, chat_id, message_id, parse_mode="HTML")

    elif call.data.startswith('sel_'):
        data_string = call.data.replace('sel_', '')
        parts = data_string.split('_', 1)
        srv, country = parts[0], parts[1]
        curr_db = load_data(DB_FILE, {})
        srv_stock = curr_db.get(srv, {}).get(country, [])
        
        if len(srv_stock) < 3:
            bot.send_message(chat_id, "❌ অন্তত ৩টি নাম্বার প্রয়োজন!")
            return
            
        # একসাথে ৩টি নাম্বার নেওয়া
        selected_numbers = [str(srv_stock.pop(0)) for _ in range(3)]
        curr_db[srv][country] = srv_stock
        save_data(DB_FILE, curr_db)
        
        users = load_data(USER_FILE, {})
        uid = str(call.from_user.id)
        if uid not in users:
            users[uid] = {"balance": 0.0, "ref_count": 0, "name": call.from_user.first_name, "joined": True
        
