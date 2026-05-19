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

bot = telebot.TeleBot(API_TOKEN, threaded=False)

# গ্লোবাল মেমরি ডিকশনারি অ্যাডমিনের ফাইল/টেক্সট আপলোড প্রসেস ট্র্যাকিংয়ের জন্য
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

# 🎯 ১. সার্ভিস সিলেকশন স্ক্রিন জেনারেটর
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

# 🎯 ২. নির্দিষ্ট সার্ভিসের ভেতরের দেশসমূহের তালিকা দেখার স্ক্রিন
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

    # 🎯 ৩. অ্যাডমিন কর্তৃক নির্দিষ্ট সার্ভিসে স্টক লোড করার ব্যাকএন্ড হ্যান্ডলার (ডুপ্লিকেট প্রোটেকশনসহ)
    elif call.data.startswith('addstock_'):
        srv_target = call.data.replace('addstock_', '')
        admin_id = call.from_user.id
        
        if srv_target == "CANCEL":
            if admin_id in ADMIN_UPLOAD_TEMP: del ADMIN_UPLOAD_TEMP[admin_id]
            bot.edit_message_text("❌ Upload Session Cancelled.", chat_id, message_id)
            return
            
        if admin_id not in ADMIN_UPLOAD_TEMP:
            bot.answer_callback_query(call.id, "❌ Session expired! Please upload the file/text again.", show_alert=True)
            return
            
        found_numbers = ADMIN_UPLOAD_TEMP[admin_id]
        curr_db = load_data(DB_FILE, {})
        
        if srv_target not in curr_db: 
            curr_db[srv_target] = {}
            
        added = 0
        notified_sample_country = "Global Zone"
        
        for r in found_numbers:
            clean_r = "+" + r.lstrip('+')
            flag = detect_country_flag(clean_r)
            try: name = geocoder.description_for_number(phonenumbers.parse(clean_r), "en")
            except: name = "Unknown"
            c_name = f"{flag} {name}" if name != "Unknown" else f"📍 Zone +{clean_r[1:4]}"
            
            if c_name not in curr_db[srv_target]: 
                curr_db[srv_target][c_name] = []
                
            # একই সার্ভিসের স্টকে নম্বরটি ডুপ্লিকেট কি না তা যাচাই করা হচ্ছে (অন্য সার্ভিসে থাকলে বাধা দেবে না)
            if clean_r not in curr_db[srv_target][c_name]:
                curr_db[srv_target][c_name].append(clean_r)
                notified_sample_country = c_name
                added += 1
                
        save_data(DB_FILE, curr_db)
        del ADMIN_UPLOAD_TEMP[admin_id]
        
        if added > 0:
            bot.edit_message_text(f"✅ Successfully loaded {added} unique numbers to {SERVICES[srv_target]['name']}.", chat_id, message_id)
            
            # 🎯 ৪. প্রিমিয়াম গ্লোবাল ইউজার নোটিফিকেশন সিস্টেম ব্রডকাস্ট 📢
            alert_msg = (
                f"📢 <b>New Fresh Stock Added!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🛠 <b>Service:</b> {SERVICES[srv_target]['icon']} {SERVICES[srv_target]['name']}\n"
                f"🌍 <b>Country Added:</b> {notified_sample_country}\n"
                f"⚡ <b>Status:</b> High Traffic Live Now 🔥\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <i>সবাই দ্রুত কাজ শুরু করুন এবং ওটিপি সংগ্রহ করুন!</i>"
            )
            all_users = load_data(USER_FILE, {})
            for u in all_users.keys():
                try: 
                    bot.send_message(int(u), alert_msg, parse_mode="HTML")
                    time.sleep(0.04)
                except: pass
        else:
            bot.edit_message_text("⚠️ No new or unique numbers were added. All were duplicates in this service.", chat_id, message_id)

    # 🎯 ৫. ইউজার কর্তৃক নম্বর গেট করার মাল্টি-সার্ভিস ইঞ্জিন মডিউল
    elif call.data.startswith('sel_'):
        data_string = call.data.replace('sel_', '')
        parts = data_string.split('_', 1)
        
        if len(parts) < 2: return
        service_key = parts[0]
        country = parts[1]
        
        curr_db = load_data(DB_FILE, {})
        srv_stock = curr_db.get(service_key, {}).get(country, [])
        
        if len(srv_stock) < 1:
            bot.answer_callback_query(call.id, "❌ স্টক শেষ!", show_alert=True)
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
        
        if not delivered_numbers:
            bot.answer_callback_query(call.id, "❌ স্টক শেষ!", show_alert=True)
            return

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
        
        bot.edit_message_text(
            text=msg_text, 
            chat_id=chat_id, 
            message_id=message_id, 
            reply_markup=json.dumps(custom_markup), 
            parse_mode="Markdown"
        )

    elif call.data == "back_c":
        send_service_list(chat_id, message_id)

    elif call.data == "conf_export":
        if int(uid) != ADMIN_ID: return
        curr_db = load_data(DB_FILE, {})
        filename = "live_stock.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("📊 PREMIUM SMS BOT - LIVE UNUSED STOCK REPORT\n")
                f.write(f"📅 Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
                for s_key, s_val in SERVICES.items():
                    f.write(f"=== {s_val['name']} Stock ===\n")
                    srv_stock = curr_db.get(s_key, {})
                    for country, numbers in sorted(srv_stock.items()):
                        if numbers:
                            f.write(f"[{country}] - Available: {len(numbers)}\n")
                            for num in numbers: f.write(f"{num}\n")
                    f.write("\n")
            with open(filename, "rb") as doc:
                bot.send_document(chat_id, doc, caption="📊 Live data stock file.")
            bot.answer_callback_query(call.id, "✅ Stock exported successfully!")
        except Exception as e:
            bot.send_message(chat_id, f"❌ File creation error: {e}")
        finally:
            if os.path.exists(filename): os.remove(filename)

    elif call.data == "conf_clear":
        curr_db = load_data(DB_FILE, {})
        markup = types.InlineKeyboardMarkup(row_width=1)
        for s_key, s_val in SERVICES.items():
            markup.add(types.InlineKeyboardButton(f"🗑️ Clear {s_val['name']} Stock", callback_data=f"rmvsrv_{s_key}"))
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_settings"))
        bot.edit_message_text("🗑️ **Select service to clear completely:**", chat_id, message_id, reply_markup=markup)

    elif call.data.startswith('rmvsrv_'):
        srv_to_rm = call.data.replace('rmvsrv_', '')
        curr_db = load_data(DB_FILE, {})
        if srv_to_rm in curr_db:
            curr_db[srv_to_rm] = {}
            save_data(DB_FILE, curr_db)
            bot.answer_callback_query(call.id, f"✅ {SERVICES[srv_to_rm]['name']} stock cleared!")
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
        try: 
            bot.send_message(int(u), message.text)
            time.sleep(0.05)
        except: pass
    bot.send_message(message.chat.id, "✅ Broadcast Done!")

def main():
    print("Clearing webhooks and starting bot...")
    try: bot.remove_webhook()
    except: pass
    print("Shop Bot is successfully running online via Master...")
    bot.infinity_polling(none_stop=True, timeout=60, long_polling_timeout=30)

if __name__ == "__main__":
    main()
        
