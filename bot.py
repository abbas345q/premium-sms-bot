import telebot
from telebot import types
import re
import os
import requests
import phonenumbers
from phonenumbers import geocoder

# --- CONFIGURATION ---
API_TOKEN = '7634786660:AAHvY09ndmYnO6pLpz_84rSLqGUEMlfwNd4'
ADMIN_ID = 6781949890
OTP_GROUP_LINK = "https://t.me/Premium_OTP_chat"
OTP_GROUP_ID = -1002295608331
STORAGE_CHANNEL_ID = -1003939878812  # ক্লাউড স্টোরেজ চ্যানেল আইডি

bot = telebot.TeleBot(API_TOKEN, threaded=False)
processed_otps = set()
admin_states = {}  # অ্যাডমিন ইনপুট ট্র্যাকিং

# --- 📁 TXT BASED CLOUD STORAGE ENGINE ---
def get_cloud_stock():
    """চ্যানেল থেকে স্টক টেক্সট ফাইল ডাউনলোড করে নাম্বারের লিস্ট রিড করার মেথড"""
    try:
        url = f"https://api.telegram.com/bot{API_TOKEN}/getChatHistory"
        response = requests.post(url, json={"chat_id": STORAGE_CHANNEL_ID, "limit": 20}).json()
        if response.get("ok") and response.get("result"):
            for msg in response["result"]:
                if msg.get("document") and msg["document"]["file_name"] == "ACTIVE_STOCK.txt":
                    f_info = bot.get_file(msg["document"]["file_id"])
                    content = bot.download_file(f_info.file_path).decode('utf-8')
                    
                    stock_db = {}
                    current_country = None
                    for line in content.split('\n'):
                        line = line.strip()
                        if not line: continue
                        if line.startswith('[') and line.endswith(']'):
                            current_country = line[1:-1]
                            stock_db[current_country] = []
                        elif current_country and line.startswith('+'):
                            stock_db[current_country].append(line)
                    return stock_db
    except Exception as e:
        print(f"Stock Read Error: {e}")
    return {}

def save_cloud_stock(stock_db):
    """স্টক ডেটাকে সুন্দর ফরম্যাটেড টেক্সট ফাইল বানিয়ে চ্যানেলে পুশ করার মেথড"""
    try:
        filename = "ACTIVE_STOCK.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for country, numbers in stock_db.items():
                if numbers:
                    f.write(f"[{country}]\n")
                    for num in numbers:
                        f.write(f"{num}\n")
                    f.write("\n")
                    
        # ওল্ড ফাইল ক্লিনআপ
        try:
            res = requests.post(f"https://api.telegram.com/bot{API_TOKEN}/getChatHistory", json={"chat_id": STORAGE_CHANNEL_ID, "limit": 10}).json()
            if res.get("ok") and res.get("result"):
                for m in res["result"]:
                    if m.get("document") and m["document"]["file_name"] == filename:
                        bot.delete_message(STORAGE_CHANNEL_ID, m["message_id"])
        except: pass

        with open(filename, 'rb') as f:
            bot.send_document(STORAGE_CHANNEL_ID, f, caption="📊 Current Live Stock File")
        if os.path.exists(filename): os.remove(filename)
    except Exception as e:
        print(f"Stock Save Error: {e}")

# --- 👤 USER SESSION CLOUD SYSTEM ---
def get_cloud_users():
    try:
        url = f"https://api.telegram.com/bot{API_TOKEN}/getChatHistory"
        response = requests.post(url, json={"chat_id": STORAGE_CHANNEL_ID, "limit": 20}).json()
        if response.get("ok") and response.get("result"):
            for msg in response["result"]:
                if msg.get("document") and msg["document"]["file_name"] == "USERS_DATA.txt":
                    f_info = bot.get_file(msg["document"]["file_id"])
                    content = bot.download_file(f_info.file_path).decode('utf-8')
                    return eval(content)
    except: pass
    return {}

def save_cloud_users(users_data):
    try:
        filename = "USERS_DATA.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(str(users_data))
        try:
            res = requests.post(f"https://api.telegram.com/bot{API_TOKEN}/getChatHistory", json={"chat_id": STORAGE_CHANNEL_ID, "limit": 10}).json()
            if res.get("ok") and res.get("result"):
                for m in res["result"]:
                    if m.get("document") and m["document"]["file_name"] == filename:
                        bot.delete_message(STORAGE_CHANNEL_ID, m["message_id"])
        except: pass
        with open(filename, 'rb') as f:
            bot.send_document(STORAGE_CHANNEL_ID, f, caption="👥 Users Database Sync")
        if os.path.exists(filename): os.remove(filename)
    except: pass

# --- ⚙️ SETTINGS SYSTEM ---
def get_settings():
    try:
        url = f"https://api.telegram.com/bot{API_TOKEN}/getChatHistory"
        response = requests.post(url, json={"chat_id": STORAGE_CHANNEL_ID, "limit": 20}).json()
        if response.get("ok") and response.get("result"):
            for msg in response["result"]:
                if msg.get("document") and msg["document"]["file_name"] == "SETTINGS.txt":
                    f_info = bot.get_file(msg["document"]["file_id"])
                    return eval(bot.download_file(f_info.file_path).decode('utf-8'))
    except: pass
    return {"ref_bonus": 2.0, "min_withdraw": 500.0, "channels": []}

def save_settings(data):
    try:
        filename = "SETTINGS.txt"
        with open(filename, 'w', encoding='utf-8') as f: f.write(str(data))
        with open(filename, 'rb') as f: bot.send_document(STORAGE_CHANNEL_ID, f)
        if os.path.exists(filename): os.remove(filename)
    except: pass

def is_user_joined_all(user_id):
    cfg = get_settings()
    if not cfg.get('channels'): return True
    for ch in cfg['channels']:
        try:
            m = bot.get_chat_member(ch['username'], user_id)
            if m.status not in ['member', 'administrator', 'creator']: return False
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
        parsed = phonenumbers.parse(f"+{num_str.lstrip('+')}")
        reg = phonenumbers.region_code_for_number(parsed)
        return "".join(chr(ord(c) + 127397) for c in reg.upper()) if reg else "📍"
    except: return "📍"

def send_country_list(chat_id, message_id=None):
    stock = get_cloud_stock()
    # এখানে লজিক পরিবর্তন করা হয়েছে: স্টকে অন্তত ১টি নাম্বার থাকলেই কান্ট্রি শো করবে
    active = {k: v for k, v in stock.items() if v and len(v) >= 1}
    if not active:
        msg_text = "❌ **No stock available right now. Please add numbers first.**"
        if message_id:
            try: bot.edit_message_text(msg_text, chat_id, message_id)
            except: pass
        else:
            bot.send_message(chat_id, msg_text)
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for c in sorted(active.keys()):
        markup.add(types.InlineKeyboardButton(f"{c} ({len(active[c])})", callback_data=f"buy_{c}"))
    
    txt = "📍 **Select Country to Purchase Number:**"
    if message_id:
        try: bot.edit_message_text(txt, chat_id, message_id, reply_markup=markup)
        except: pass
    else: 
        bot.send_message(chat_id, txt, reply_markup=markup)

# --- 🚀 ADVANCED FORWARDING ENGINE ---
def process_single_otp_message(txt):
    if not txt: return
    num_parts = re.findall(r'\d+', txt)
    if not num_parts: return
    
    group_last_4 = num_parts[-1][-4:] if len(num_parts[-1]) >= 4 else num_parts[-1]
    if len(group_last_4) < 3: return

    users = get_cloud_users()
    for uid, info in users.items():
        active_numbers = info.get("active_numbers", [])
        for num_obj in active_numbers:
            clean_num = re.sub(r'\D', '', num_obj["number"])
            user_last_4 = clean_num[-4:]
            
            if group_last_4 in user_last_4 or user_last_4 in group_last_4:
                otp_match = re.search(r'(?:OTP|code|🧑‍💻)[:\s]*(\d+)', txt, re.IGNORECASE)
                if otp_match: otp_code = otp_match.group(1)
                else:
                    all_digits = re.findall(r'\b\d{4,8}\b', txt)
                    possible = [d for d in all_digits if d not in num_parts]
                    otp_code = possible[0] if possible else "Not Found"

                ukey = f"{uid}_{user_last_4}_{otp_code}"
                if ukey in processed_otps: return
                processed_otps.add(ukey)

                srv = "Unknown"
                for app in ["Telegram", "WhatsApp", "Imo", "Facebook", "Google", "TikTok", "Viber"]:
                    if app.lower() in txt.lower(): srv = app; break

                final_msg = (
                    f"✨ **NEW OTP RECEIVED!**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Service:** {srv}\n"
                    f"🔢 **Matched Number:** `{num_obj['number']}`\n"
                    f"🔑 **OTP Code:** `{otp_code}`\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                try: bot.send_message(int(uid), final_msg, parse_mode="Markdown")
                except: pass
                return

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = str(message.from_user.id)
    if not is_user_joined_all(message.from_user.id):
        cfg = get_settings()
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(cfg.get('channels', []), 1):
            markup.add(types.InlineKeyboardButton(f"📢 Join Channel {i}", url=ch['link']))
        markup.add(types.InlineKeyboardButton("✅ Verify Join", callback_data="verify_join"))
        bot.send_message(message.chat.id, "⚠️ **You must join our channels first!**", reply_markup=markup)
        return

    users = get_cloud_users()
    if uid not in users:
        users[uid] = {"balance": 0.0, "ref_count": 0, "name": message.from_user.first_name, "active_numbers": []}
        save_cloud_users(users)
    bot.send_message(message.chat.id, f"👋 Welcome {message.from_user.first_name}!", reply_markup=main_keyboard())

@bot.message_handler(commands=['settings'])
def admin_settings(message):
    if int(message.from_user.id) != ADMIN_ID: return
    cfg = get_settings()
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Set Refer", callback_data="set_ref"),
        types.InlineKeyboardButton("🏧 Set Min Withdraw", callback_data="set_wit"),
        types.InlineKeyboardButton("📢 Channels", callback_data="manage_ch"),
        types.InlineKeyboardButton("🗑️ Clear Stock", callback_data="clear_stk"),
        types.InlineKeyboardButton("📢 Broadcast Msg", callback_data="broadcast_msg")
    )
    bot.send_message(message.chat.id, f"🛠 **Admin Panel**\n\nRefer Bonus: {cfg['ref_bonus']} BDT\nMin Withdraw: {cfg['min_withdraw']} BDT", reply_markup=markup)

@bot.message_handler(func=lambda message: message.chat.id == OTP_GROUP_ID)
def listen_group(message):
    txt = message.text or message.caption or ""
    process_single_otp_message(txt)

@bot.message_handler(content_types=['text', 'document'])
def handle_all(message):
    if message.chat.id == OTP_GROUP_ID: return
    uid = str(message.from_user.id)

    if message.text == "📞 Get Number":
        send_country_list(message.chat.id)
    elif message.text == "💰 Balance":
        users = get_cloud_users()
        bot.send_message(message.chat.id, f"💳 Balance: {users.get(uid, {}).get('balance', 0.0)} BDT")
    elif message.text == "🌍 Available Countries":
        stock = get_cloud_stock()
        active = [f"✅ {k} ({len(v)})" for k, v in stock.items() if v and len(v) >= 1]
        bot.send_message(message.chat.id, "🌍 Stock List:\n\n" + "\n".join(active) if active else "❌ Stock Empty")
    
    # 📝 এডমিন ফাইল আপলোড ও নাম্বার ফিল্টারিং সিস্টেম
    elif int(message.from_user.id) == ADMIN_ID and message.content_type == 'document':
        f_info = bot.get_file(message.document.file_id)
        txt = bot.download_file(f_info.file_path).decode('utf-8')
        
        found = re.findall(r'\+?\d{9,15}', txt)
        if found:
            stock = get_cloud_stock()
            added = 0
            for r in found:
                clean_num = "+" + r.lstrip('+')
                flag = detect_country_flag(clean_num)
                try: 
                    name = geocoder.description_for_number(phonenumbers.parse(clean_num), "en")
                except: 
                    name = "Zone"
                
                c_name = f"{flag} {name}"
                if c_name not in stock: stock[c_name] = []
                if clean_num not in stock[c_name]:
                    stock[c_name].append(clean_num)
                    added += 1
            
            save_cloud_stock(stock)
            bot.reply_to(message, f"✅ Successfully parsed and added {added} numbers to Live Stock!")
        else:
            bot.reply_to(message, "❌ No valid numbers found inside the uploaded file.")

    # ⚙️ অ্যাডমিন স্টেট প্রসেসিং
    elif int(message.from_user.id) == ADMIN_ID and uid in admin_states:
        state = admin_states.pop(uid)
        cfg = get_settings()
        
        if state == "ref":
            try:
                cfg["ref_bonus"] = float(message.text)
                save_settings(cfg)
                bot.send_message(message.chat.id, "✅ Refer bonus updated successfully!")
            except: bot.send_message(message.chat.id, "❌ Invalid Amount.")
            
        elif state == "wit":
            try:
                cfg["min_withdraw"] = float(message.text)
                save_settings(cfg)
                bot.send_message(message.chat.id, "✅ Min withdraw updated successfully!")
            except: bot.send_message(message.chat.id, "❌ Invalid Amount.")
            
        elif state == "broadcast":
            users = get_cloud_users()
            count = 0
            for u in users.keys():
                try:
                    bot.send_message(int(u), f"📢 **ADMIN BROADCAST**\n\n{message.text}", parse_mode="Markdown")
                    count += 1
                except: pass
            bot.send_message(message.chat.id, f"✅ Broadcast finished. Sent to {count} users.")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    uid = str(call.from_user.id)

    # ক্যালেরি বাটন রেসপন্স নিশ্চিত করার জন্য প্রথমেই answer করা হলো
    bot.answer_callback_query(call.id)

    if call.data == "verify_join":
        if is_user_joined_all(call.from_user.id):
            try: bot.delete_message(chat_id, message_id)
            except: pass
            handle_start(call.message)
        else: bot.send_message(chat_id, "❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি!")

    elif call.data == "set_ref":
        admin_states[uid] = "ref"
        bot.send_message(chat_id, "✍️ Enter new refer bonus amount:")
    elif call.data == "set_wit":
        admin_states[uid] = "wit"
        bot.send_message(chat_id, "✍️ Enter new min withdraw amount:")
    elif call.data == "clear_stk":
        save_cloud_stock({})
        bot.send_message(chat_id, "🗑️ Stock completely cleared!")
    elif call.data == "broadcast_msg":
        admin_states[uid] = "broadcast"
        bot.send_message(chat_id, "✍️ Send the message you want to broadcast to all users:")

    elif call.data.startswith('buy_'):
        country = call.data.replace('buy_', '')
        stock = get_cloud_stock()
        
        # এখানে লজিক পরিবর্তন: ১ বা তার বেশি নাম্বার থাকলেও কেনা যাবে
        if country in stock and len(stock[country]) >= 1:
            users = get_cloud_users()
            if uid not in users: users[uid] = {"balance": 0.0, "ref_count": 0, "name": call.from_user.first_name, "active_numbers": []}
            
            delivered = []
            # স্টকে যতগুলো আছে (সর্বোচ্চ ৩টি) ততগুলোই ইউজারকে দেওয়া হবে
            take_count = min(3, len(stock[country]))
            for _ in range(take_count):
                if stock[country]:
                    delivered.append(stock[country].pop(0))
            
            users[uid]["active_numbers"] = [{"number": n, "country": country} for n in delivered]
            
            save_cloud_stock(stock)
            save_cloud_users(users)

            num_text = "\n".join([f"`{n}`" for n in delivered])
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("🔄 CHANGE NUMBERS", callback_data=f"buy_{country}"),
                types.InlineKeyboardButton("🚀 GET OTP", url=OTP_GROUP_LINK)
            )
            msg_text = f"🌍 **Country:** {country}\n━━━━━━━━━━━━━━\n{num_text}\n━━━━━━━━━━━━━━\n💡 **Tap number to copy!**"
            try: bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
            except: bot.send_message(chat_id, msg_text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"❌ This country ({country}) runs out of stock!")

if __name__ == "__main__":
    print("Railway multi-fix stock engine active...")
    bot.infinity_polling(none_stop=True)
                        
