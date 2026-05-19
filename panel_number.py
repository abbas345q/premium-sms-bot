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

# (পূর্বের ফাংশনগুলো অপরিবর্তিত রাখা হয়েছে)
def is_user_joined_all(user_id):
    if not config.get('channels'): return True
    for ch in config['channels']:
        try:
            member = bot.get_chat_member(ch['username'], user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

def detect_country_flag(num_str):
    try:
        full_num = f"+{num_str.lstrip('+')}"
        parsed = phonenumbers.parse(full_num)
        region = phonenumbers.region_code_for_number(parsed)
        return "".join(chr(ord(c) + 127397) for c in region.upper()) if region else "📍"
    except: return "📍"

# --- মেইন হ্যান্ডলার যেখানে কপি সিস্টেম ঠিক করা হয়েছে ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    uid = str(call.from_user.id)
    
    # ... (অন্যান্য কন্ডিশনগুলো ঠিক থাকবে) ...

    if call.data.startswith('sel_'):
        data_string = call.data.replace('sel_', '')
        parts = data_string.split('_', 1)
        if len(parts) < 2: return
        service_key, country = parts[0], parts[1]
        
        curr_db = load_data(DB_FILE, {})
        srv_stock = curr_db.get(service_key, {}).get(country, [])
        
        if len(srv_stock) < 1:
            bot.answer_callback_query(call.id, "❌ স্টক শেষ!", show_alert=True)
            return
            
        # ৩টি নাম্বার নেওয়া
        delivered_numbers = [str(srv_stock.pop(0)) for _ in range(min(3, len(srv_stock)))]
        curr_db[service_key][country] = srv_stock
        save_data(DB_FILE, curr_db)
        
        flag_icon = country.split()[0] if country.split() else "🌍"
        
        # এখানে কপি বাটন সিস্টেম তৈরি (আপনার দ্বিতীয় কোডের লজিক)
        inline_keyboard = []
        for num in delivered_numbers:
            inline_keyboard.append([{
                "text": f"{flag_icon} {num}", 
                "copy_text": {"text": str(num)}
            }])
        
        # কন্ট্রোল বাটন
        inline_keyboard.append([{"text": "🔄 CHANGE NUMBERS", "callback_data": f"sel_{service_key}_{country}"}])
        inline_keyboard.append([{"text": "🌐 CHANGE COUNTRY", "callback_data": f"show_srv_{service_key}"}])
        inline_keyboard.append([{"text": "🚀 GET OTP", "url": OTP_GROUP_LINK}])
        
        # টেলিগ্রাম এপিআইতে সরাসরি রিকোয়েস্ট পাঠানো
        import requests
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": f"🌍 **Country:** {country}\n⚙️ **Service:** {SERVICES[service_key]['icon']} {SERVICES[service_key]['name']}\n\n✅ **Click to copy:**",
            "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": inline_keyboard}
        }
        requests.post(f"https://api.telegram.org/bot{API_TOKEN}/editMessageText", json=payload)
        bot.answer_callback_query(call.id)

    # ... (বাকি সব কোড আগের মতোই থাকবে) ...

def main():
    bot.infinity_polling(none_stop=True)

if __name__ == "__main__":
    main()
