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
        if message_id: bot.edit_message_text(txt, chat_id, message_id, reply_markup=markup)
        else: bot.send_message(chat_id, txt, reply_markup=markup)
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
        send_country_list(message.chat.id)
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
        active = [f"✅ {k} ({len(v)})" for k, v in current_db.items() if v and len(v) > 0]
        bot.send_message(message.chat.id, "🌍 Stock List:\n\n" + "\n".join(active) if active else "❌ Empty")
    
    elif int(message.from_user.id) == ADMIN_ID:
        txt = message.text if message.text else ""
        if message.content_type == 'document':
            f_info = bot.get_file(message.document.file_id)
            txt = bot.download_file(f_info.file_path).decode('utf-8')
        
        found = re.findall(r'\+?\d{9,15}', txt)
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
            
            users[uid]["active_numbers"] = []
            delivered_numbers = []
            take_count = min(3, len(curr_db[country]))
            for _ in range(take_count):
                if curr_db[country]:
                    raw_num = str(curr_db[country].pop(0))
                    delivered_numbers.append(raw_num)
                    users[uid]["active_numbers"].append({"number": raw_num, "country": country})
            
            save_data(DB_FILE, curr_db)
            save_data(USER_FILE, users)
            
            if not delivered_numbers:
                bot.answer_callback_query(call.id, "❌ স্টক শেষ!", show_alert=True)
                return

            # 📌 মেইন বটের বাটন জেনারেটর ইঞ্জিন (র-মেথড) শুরু 🚀
            raw_keyboard = []
            
            # দেশের নাম থেকে শুধু কান্ট্রি ফ্ল্যাগ বা প্রথম ইমোজিটা আলাদা করে নেওয়া হচ্ছে
            flag_icon = country.split()[0] if country.split() else "🌍"
            
            # ডেলিভারি হওয়া নম্বরগুলোকে বাটন আকারে সাজানো হচ্ছে (কোনো এক্সট্রা লোগো ছাড়া, শুধু পতাকা ও নম্বর)
            for num in delivered_numbers:
                btn_text = f"{flag_icon} {num}"
                number_button = {
                    "text": btn_text,
                    "copy_text": {"text": str(num)} # এই মেথডটি বাটনের পাশে অরিজিনাল কপি সাইন নিয়ে আসবে
                }
                raw_keyboard.append([number_button])
                
            # কন্ট্রোল বাটনগুলো নিচে যুক্ত করা হলো
            raw_keyboard.append([{"text": "🔄 CHANGE NUMBERS", "callback_data": f"sel_{country}"}])
            raw_keyboard.append([{"text": "🌐 CHANGE COUNTRY", "callback_data": "back_c"}])
            raw_keyboard.append([{"text": "🚀 GET OTP", "url": OTP_GROUP_LINK}])
            
            custom_markup = {"inline_keyboard": raw_keyboard}
            
            # আপনার মেইন ডিসপ্লে মেসেজ টেক্সট
            msg_text = f"🌍 **Country:** {country}\n━━━━━━━━━━━━━━\n⏳ **Waiting for OTP...**"
            
            bot.edit_message_text(
                text=msg_text, 
                chat_id=chat_id, 
                message_id=message_id, 
                reply_markup=json.dumps(custom_markup), 
                parse_mode="Markdown"
            )
        else: bot.answer_callback_query(call.id, "❌ স্টক শেষ!", show_alert=True)

    elif call.data == "back_c":
        send_country_list(chat_id, message_id)

    elif call.data == "conf_export":
        if int(uid) != ADMIN_ID: return
        curr_db = load_data(DB_FILE, {})
        active_stock = {k: v for k, v in curr_db.items() if v and len(v) > 0}
        if not active_stock:
            bot.answer_callback_query(call.id, "❌ Database stock is completely empty!", show_alert=True)
            return
        filename = "live_stock.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("📊 PREMIUM SMS BOT - LIVE UNUSED STOCK REPORT\n")
                f.write(f"📅 Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
                for country, numbers in sorted(active_stock.items()):
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
    
