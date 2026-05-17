import telebot
from telebot import types
import re
import json
import os
import time
import requests
import phonenumbers
from phonenumbers import geocoder

# --- CONFIGURATION ---
API_TOKEN = '7634786660:AAHvY09ndmYnO6pLpz_84rSLqGUEMlfwNd4'
ADMIN_ID = 6781949890
OTP_GROUP_LINK = "https://t.me/Premium_OTP_chat"
OTP_GROUP_ID = -1002295608331

# 📢 আপনার নতুন দেওয়া সিক্রেট ব্যাকআপ চ্যানেল আইডি (১০০% কনফিগারড)
STORAGE_CHANNEL_ID = -1003939878812  

bot = telebot.TeleBot(API_TOKEN, threaded=False)
processed_otps = set()

# --- CLOUD TELEGRAM STORAGE ENGINE ---
def get_cloud_data(filename, default):
    """টেলিগ্রাম ক্লাউড চ্যানেল থেকে ডাটাবেজ ফাইল রিড করার মেথড"""
    try:
        url = f"https://api.telegram.com/bot{API_TOKEN}/getChatHistory"
        response = requests.post(url, json={"chat_id": STORAGE_CHANNEL_ID, "limit": 50}).json()
        if response.get("ok") and response.get("result"):
            for msg in response["result"]:
                if msg.get("document") and msg["document"]["file_name"] == filename:
                    f_info = bot.get_file(msg["document"]["file_id"])
                    content = bot.download_file(f_info.file_path)
                    return json.loads(content.decode('utf-8'))
    except Exception as e:
        print(f"Cloud Read Error for {filename}: {e}")
    return default

def save_cloud_data(filename, data):
    """টেলিগ্রাম ক্লাউড চ্যানেলে ডাটাবেজ ফাইল রাইট/আপডেট করার মেথড"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        
        # চ্যানেলে থাকা পুরনো ব্যাকআপ ফাইলটি ডিলিট করা (মেমোরি ক্লিন রাখার জন্য)
        try:
            res = requests.post(f"https://api.telegram.com/bot{API_TOKEN}/getChatHistory", json={"chat_id": STORAGE_CHANNEL_ID, "limit": 20}).json()
            if res.get("ok") and res.get("result"):
                for m in res["result"]:
                    if m.get("document") and m["document"]["file_name"] == filename:
                        bot.delete_message(STORAGE_CHANNEL_ID, m["message_id"])
        except:
            pass
            
        with open(filename, 'rb') as f:
            bot.send_document(STORAGE_CHANNEL_ID, f, caption=f"🔄 Cloud Database Auto-Synced: {filename}")
        
        # লোকাল স্পেস ক্লিন রাখা
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        print(f"Cloud Save Error for {filename}: {e}")

# --- CHANNEL MEMBERSHIP CHECK ---
def is_user_joined_all(user_id):
    config = get_cloud_data('settings.json', {"ref_bonus": 2.0, "min_withdraw": 500.0, "channels": []})
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

def send_country_list(chat_id, message_id=None):
    curr_db = get_cloud_data('numbers_db.json', {})
    active = {k: v for k, v in curr_db.items() if isinstance(v, list) and len(v) > 0}
    if not active:
        bot.send_message(chat_id, "❌ **No stock available right now.**")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for c in sorted(active.keys()):
        markup.add(types.InlineKeyboardButton(f"{c} ({len(active[c])})", callback_data=f"sel_{c}"))
    
    txt = "📍 **Select Country to Purchase Number:**"
    if message_id:
        try: bot.edit_message_text(txt, chat_id, message_id, reply_markup=markup)
        except: pass
    else:
        bot.send_message(chat_id, txt, reply_markup=markup)

# --- CORE OTP MATCHING & FORWARDING ENGINE ---
def process_single_otp_message(txt):
    if not txt: return
    
    # গ্রুপ মেসেজ থেকে সংখ্যাগুলো আলাদা করা
    num_parts = re.findall(r'\d+', txt)
    if not num_parts: return
    
    # লাস্ট অংশটিই মাস্কড বা নরমাল নাম্বারের শেষ ৪ ডিজিট নির্দেশ করে
    group_last_4 = num_parts[-1]
    if len(group_last_4) < 4: return
    group_last_4 = group_last_4[-4:]

    # রিয়েলটাইম ক্লাউড স্টোরেজ থেকে একটিভ ইউজার সেশন ডাটাবেজ রিড করা হচ্ছে
    local_users = get_cloud_data('users_data.json', {})
    if not local_users: return

    for uid_str, u_info in local_users.items():
        active_list = u_info.get("active_numbers", [])
        if not active_list: continue
        
        for num_obj in active_list:
            clean_num = re.sub(r'\D', '', num_obj["number"])
            if len(clean_num) < 4: continue
            user_last_4 = clean_num[-4:]
            
            # 🔥 ম্যাচিং লজিক: ওটিপি গ্রুপ লাস্ট ৪ == ইউজারের একটিভ নাম্বার লাস্ট ৪ 🔥
            if group_last_4 == user_last_4:
                # ওটিপি কোড পার্স করা
                otp_match = re.search(r'(?:OTP|code)[:\s]*(\d+)', txt, re.IGNORECASE)
                if otp_match:
                    otp_code = otp_match.group(1)
                else:
                    all_digits = re.findall(r'\b\d{4,8}\b', txt)
                    possible_codes = [d for d in all_digits if d not in num_parts]
                    otp_code = possible_codes[0] if possible_codes else "Not Found"

                # ডুপ্লিকেট ওটিপি ফরওয়ার্ড লক
                unique_key = f"{uid_str}_{user_last_4}_{otp_code}"
                if unique_key in processed_otps: return
                processed_otps.add(unique_key)

                # অ্যাপ আইডেন্টিফিকেশন
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
                    f"🔢 **Matched Number:** `...{user_last_4}`\n"
                    f"🔑 **OTP Code:** `{otp_code}`\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                try:
                    bot.send_message(int(uid_str), final_msg, parse_mode="Markdown")
                except: pass
                return

# --- TELEGRAM HANDLERS ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = str(message.from_user.id)
    name = message.from_user.first_name
    
    if not is_user_joined_all(message.from_user.id):
        config = get_cloud_data('settings.json', {"channels": []})
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(config.get('channels', []), 1):
            markup.add(types.InlineKeyboardButton(f"📢 Join Channel {i}", url=ch['link']))
        markup.add(types.InlineKeyboardButton("✅ Verify Join", callback_data="verify_join"))
        bot.send_message(message.chat.id, "⚠️ **You must join our channels to use this bot!**", reply_markup=markup, parse_mode="Markdown")
        return

    users = get_cloud_data('users_data.json', {})
    if uid not in users:
        users[uid] = {"balance": 0.0, "ref_count": 0, "name": name, "joined": True, "active_numbers": []}
        save_cloud_data('users_data.json', users)

    welcome_msg = f"👋 **Hello, {name}!**\n✨ **Welcome to PREMIUM SMS PANEL**\n🚀 *Fastest Auto OTP Service.*"
    bot.send_message(message.chat.id, welcome_msg, reply_markup=main_keyboard(), parse_mode="Markdown")

@bot.message_handler(commands=['settings'])
def admin_settings(message):
    if int(message.from_user.id) != ADMIN_ID: return
    config = get_cloud_data('settings.json', {"ref_bonus": 2.0, "min_withdraw": 500.0, "channels": []})
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⚙️ Manage Channels", callback_data="conf_chan"),
        types.InlineKeyboardButton("🗑️ Clear Stock", callback_data="conf_clear")
    )
    text = f"🛠 **Admin Panel**\n💰 Refer Bonus: {config['ref_bonus']} BDT\n🏧 Min Withdraw: {config['min_withdraw']} BDT"
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.chat.id == OTP_GROUP_ID)
def listen_otp_group(message):
    txt = message.text if message.text else (message.caption if message.caption else "")
    process_single_otp_message(txt)

@bot.message_handler(content_types=['text', 'document'])
def handle_all(message):
    if message.chat.id == OTP_GROUP_ID: return
    uid = str(message.from_user.id)
    
    if message.text == "📞 Get Number":
        send_country_list(message.chat.id)
    elif message.text == "💰 Balance":
        users = get_cloud_data('users_data.json', {})
        bot.send_message(message.chat.id, f"💳 **Current Balance:** {users.get(uid, {}).get('balance', 0.0)} BDT")
    elif message.text == "🌍 Available Countries":
        current_db = get_cloud_data('numbers_db.json', {})
        active = [f"✅ {k} ({len(v)})" for k, v in current_db.items() if v and len(v) > 0]
        bot.send_message(message.chat.id, "🌍 Stock List:\n\n" + "\n".join(active) if active else "❌ Empty")
    
    # 📝 এডমিন যখন ডক/টেক্সট ফাইল আপলোড করবে, ডিরেক্ট ক্লাউড ডাটাবেজে স্টোর হবে
    elif int(message.from_user.id) == ADMIN_ID and message.content_type == 'document':
        f_info = bot.get_file(message.document.file_id)
        txt = bot.download_file(f_info.file_path).decode('utf-8')
        found = re.findall(r'\d{7,16}', txt)
        if found:
            curr_db = get_cloud_data('numbers_db.json', {})
            added = 0
            for r in found:
                flag = detect_country_flag(r)
                try: name = geocoder.description_for_number(phonenumbers.parse(f"+{r.lstrip('+')}"), "en")
                except: name = "Unknown"
                c_name = f"{flag} {name}" if name != "Unknown" else f"📍 Zone +{r[:3]}"
                if c_name not in curr_db: curr_db[c_name] = []
                num = f"+{r.lstrip('+')}"
                if num not in curr_db[c_name]:
                    curr_db[c_name].append(num)
                    added += 1
            save_cloud_data('numbers_db.json', curr_db)
            bot.reply_to(message, f"✅ Successfully loaded and backed up {added} numbers to Telegram Cloud Storage Channel.")

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
        curr_db = get_cloud_data('numbers_db.json', {})
        
        if country in curr_db and curr_db[country]:
            users = get_cloud_data('users_data.json', {})
            if uid not in users: users[uid] = {"balance": 0.0, "ref_count": 0, "name": call.from_user.first_name, "joined": True, "active_numbers": []}
            
            # আগের একটিভ নাম্বার ক্লিয়ার করে নতুনটিকে টার্গেট করা
            users[uid]["active_numbers"] = []

            # 🔄 ডিলিট অ্যান্ড পুশ: স্টক ফাইল থেকে তুলবে এবং স্টক ফাইল থেকে সাথে সাথে রিমুভ করবে
            delivered_numbers = []
            for _ in range(3):
                if curr_db[country] and len(curr_db[country]) > 0:
                    raw_num = str(curr_db[country].pop(0)) # পপ করার কারণে ফাইল থেকে ডিলিট হয়ে যাচ্ছে
                    delivered_numbers.append(raw_num)
                    users[uid]["active_numbers"].append({"number": raw_num, "country": country})
            
            # ক্লাউড ফাইলে ইনস্ট্যান্ট সিঙ্ক সেভ
            save_cloud_data('numbers_db.json', curr_db)
            save_cloud_data('users_data.json', users)
            
            if not delivered_numbers:
                bot.answer_callback_query(call.id, "❌ Out of stock!", show_alert=True)
                return

            num_text = "\n".join([f"`{n}`" for n in delivered_numbers])
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("🔄 CHANGE NUMBERS", callback_data=f"sel_{country}"),
                types.InlineKeyboardButton("🚀 GET OTP", url=OTP_GROUP_LINK)
            )
            msg_text = f"🌍 **Country:** {country}\n━━━━━━━━━━━━━━\n{num_text}\n━━━━━━━━━━━━━━\n💡 **Tap number to copy!**"
            bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "❌ Out of stock!", show_alert=True)

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    print("Railway Cloud Database Sync Bot is Live...")
    bot.infinity_polling()
    
