import requests
import time
import re
import json
import os
from datetime import datetime, timedelta
import phonenumbers
from phonenumbers import geocoder

# === CONFIGURATION ===
PANEL_NAME = "Premium OTP Panel" 
API_TOKEN = 'RlFTQ0pBUzRiZHhJVIlVioZthlVIaWZdVI-Dg3ODkUmCZHNFWISIig=='
API_BASE_URL = 'http://147.135.212.197/crapi/st/viewstats'

BOT_TOKEN = '7634786660:AAHvY09ndmYnO6pLpz_84rSLqGUEMlfwNd4'
OTP_GROUP_ID = -1002295608331
# নিশ্চিত করুন এই পাথটি আপনার বটের পাথ অনুযায়ী সঠিক আছে
USER_FILE = 'users_data.json' 
SENT_FILE = 'db_number_panel.json'

SERVICE_ICONS = {"facebook": "Facebook", "whatsapp": "WhatsApp", "telegram": "Telegram"}

LOCAL_PROCESSED_KEYS = set()

def safe_load_json(file_path, default_value):
    # ফাইল না থাকলে বা সাইজ ০ হলে ডিফল্ট ভ্যালু রিটার্ন করবে
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0: 
        return default_value
    try:
        with open(file_path, 'r', encoding='utf-8') as f: 
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return default_value

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

def send_to_telegram_group_premium(service, number, otp, full_msg):
    flag, short_name = get_country_info(number)
    srv_name = service.lower()
    clean_srv = next((v for k, v in SERVICE_ICONS.items() if k in srv_name), service.upper())
    
    text = f"{flag} <b>{short_name}</b> {clean_srv}\n<code>{number}</code>"
    payload = {
        "chat_id": OTP_GROUP_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[{"text": f"🔑 {otp}", "copy_text": {"text": str(otp)}}]]
        }
    }
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=10)
    except: pass

def send_direct_to_user_inbox(service, number, otp, full_msg):
    current_users = safe_load_json(USER_FILE, {})
    if not current_users: return

    flag, short_name = get_country_info(number)
    srv_clean = next((v for k, v in SERVICE_ICONS.items() if k in service.lower()), service.upper())

    for uid, u_info in current_users.items():
        if not isinstance(u_info, dict): continue
        active_numbers = u_info.get("active_numbers", [])
        
        for num_obj in active_numbers:
            user_full_num = str(num_obj.get("number", ""))
            user_clean_num = re.sub(r'\D', '', user_full_num)
            
            # নাম্বারের শেষ ৪ ডিজিট চেক
            if len(user_clean_num) >= 4:
                user_4_digits = user_clean_num[-4:]
                
                # যদি ওটিপি মেসেজের ভেতর ওই ৪ ডিজিট থাকে
                if user_4_digits in full_msg:
                    inbox_text = f"{flag} <b>{short_name}</b> {srv_clean}\n<code>{user_full_num}</code>"
                    payload = {
                        "chat_id": int(uid),
                        "text": inbox_text,
                        "parse_mode": "HTML",
                        "reply_markup": {
                            "inline_keyboard": [[{"text": f"🔑 {otp}", "copy_text": {"text": str(otp)}}]]
                        }
                    }
                    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=10)
                    except: pass
                    return

def main():
    initial_list = safe_load_json(SENT_FILE, [])
    for item in initial_list: LOCAL_PROCESSED_KEYS.add(str(item))

    while True:
        try:
            params = {"token": API_TOKEN, "records": "30"}
            res = requests.get(API_BASE_URL, params=params, timeout=15)
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
                            send_to_telegram_group_premium(srv, num, otp, msg)
                            send_direct_to_user_inbox(srv, num, otp, msg)
                    
                    with open(SENT_FILE, 'w', encoding='utf-8') as f:
                        json.dump(list(LOCAL_PROCESSED_KEYS), f, indent=4)
            time.sleep(3)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    main()
    
