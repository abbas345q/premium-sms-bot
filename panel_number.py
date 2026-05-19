import requests
import time
import re
import json
import os
import fcntl # ফাইল লকিং এর জন্য যুক্ত করা হয়েছে
from datetime import datetime, timedelta
import phonenumbers
from phonenumbers import geocoder

# === CONFIGURATION ===
API_TOKEN = 'RlFTQ0pBUzRiZHhJVIlVioZthlVIaWZdVI-Dg3ODkUmCZHNFWISIig=='
API_BASE_URL = 'http://147.135.212.197/crapi/st/viewstats'
BOT_TOKEN = '7634786660:AAHvY09ndmYnO6pLpz_84rSLqGUEMlfwNd4'
OTP_GROUP_ID = -1002295608331
USER_FILE = 'users_data.json' 
SENT_FILE = 'db_number_panel.json'

SERVICE_ICONS = {"facebook": "Facebook", "whatsapp": "WhatsApp", "telegram": "Telegram", "amazon": "AMAZON"}
OTP_BOT_URL = "https://t.me/Premium_SMS2_bot"
METHODS_CHANNEL_URL = "https://t.me/Earning_Tips055"

LOCAL_PROCESSED_KEYS = set()

def safe_load_json(file_path, default_value):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0: return default_value
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # ফাইল লক করা হয়েছে যাতে বট লেখার সময় প্যানেল রিড না করে
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)
            return data
    except: return default_value

def get_country_info(number):
    try:
        raw_num = str(number).strip()
        if not raw_num.startswith('+'): raw_num = '+' + raw_num
        parsed_num = phonenumbers.parse(raw_num, None)
        region_code = phonenumbers.region_code_for_number(parsed_num)
        if region_code:
            flag = "".join(chr(ord(c) + 127397) for c in region_code.upper())
            return flag, region_code.upper()
    except: pass
    return "🌐", "GL"

def detect_language(msg):
    if re.search(r'[া-ীু-ূে-ো]', msg): return "Bangla"
    return "English"

def mask_number(number):
    num_str = str(number).strip()
    return f"{num_str[:-7]}***{num_str[-4:]}" if len(num_str) > 7 else num_str

# গ্রুপ মেসেজ ফাংশন
def send_to_telegram_group_premium(service, number, otp, full_msg):
    flag, short_name = get_country_info(number)
    lang = detect_language(full_msg)
    srv_clean = next((v for k, v in SERVICE_ICONS.items() if k in service.lower()), service.upper())
    
    text = f"{flag} <b>{short_name}</b> {srv_clean}\n{mask_number(number)} [<b>{lang}</b>]"
    payload = {
        "chat_id": OTP_GROUP_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": f"🔑 {otp}", "copy_text": {"text": str(otp)}}],
                [{"text": "🔝 Number", "url": OTP_BOT_URL}, {"text": "🤖 Methods", "url": METHODS_CHANNEL_URL}]
            ]
        }
    }
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=2)
    except: pass

# ইনবক্স মেসেজ ফাংশন
def send_direct_to_user_inbox(service, number, otp, full_msg):
    current_users = safe_load_json(USER_FILE, {})
    flag, short_name = get_country_info(number)
    srv_clean = next((v for k, v in SERVICE_ICONS.items() if k in service.lower()), service.upper())

    for uid, u_info in current_users.items():
        if not isinstance(u_info, dict): continue
        for num_obj in u_info.get("active_numbers", []):
            # ইউজারের নাম্বারের লাস্ট ৪ ডিজিট চেক করা হচ্ছে
            user_number = str(num_obj.get("number", ""))
            if len(user_number) >= 4 and user_number[-4:] in full_msg:
                inbox_text = f"📩 <b>OTP Received</b>\nService: {srv_clean}\nNumber: <code>{number}</code>"
                payload = {
                    "chat_id": int(uid),
                    "text": inbox_text,
                    "parse_mode": "HTML",
                    "reply_markup": {"inline_keyboard": [[{"text": f"🔑 {otp}", "copy_text": {"text": str(otp)}}]]}
                }
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=2)
                except: pass
                # একটির বেশি ফরওয়ার্ড ঠেকাতে এখানে return বাদ দেওয়া হয়েছে যদি মাল্টিপল ইউজার একই নাম্বার নেয়
                
def main():
    initial_list = safe_load_json(SENT_FILE, [])
    for item in initial_list: LOCAL_PROCESSED_KEYS.add(str(item))

    while True:
        try:
            res = requests.get(API_BASE_URL, params={"token": API_TOKEN, "records": "30"}, timeout=10)
            if res.status_code == 200:
                records = res.json()
                if isinstance(records, list):
                    for row in reversed(records):
                        srv, num, msg = str(row[0]), str(row[1]), str(row[2])
                        otp_match = re.search(r'\b(\d{4,8})\b', msg)
                        otp = otp_match.group() if otp_match else "N/A"
                        uid_key = f"{num}_{otp}"
                        
                        if uid_key not in LOCAL_PROCESSED_KEYS:
                            LOCAL_PROCESSED_KEYS.add(uid_key)
                            # গ্রুপে পাঠানো
                            send_to_telegram_group_premium(srv, num, otp, msg)
                            # ইনবক্সে ফরওয়ার্ড করা
                            send_direct_to_user_inbox(srv, num, otp, msg)
                    
                    # ফাইল রাইট করার সময়ও লক ব্যবহার করা হয়েছে
                    with open(SENT_FILE, 'w', encoding='utf-8') as f:
                        fcntl.flock(f, fcntl.LOCK_EX)
                        json.dump(list(LOCAL_PROCESSED_KEYS), f, indent=4)
                        fcntl.flock(f, fcntl.LOCK_UN)
            time.sleep(1) 
        except: time.sleep(5)

if __name__ == "__main__":
    main()
