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
USER_FILE = 'users_data.json'
SENT_FILE = 'db_number_panel.json'

SERVICE_ICONS = {"facebook": "Facebook", "whatsapp": "WhatsApp", "telegram": "Telegram"}

# মেমরি লক (ওটিপি ডাবল হওয়া প্রতিরোধ করার জন্য)
LOCAL_PROCESSED_KEYS = set()

def mask_number(number):
    num_str = str(number).strip()
    return f"{num_str[:-7]}***{num_str[-4:]}" if len(num_str) > 7 else num_str

def get_country_info(number):
    """
    phonenumbers লাইব্রেরি ব্যবহার করে পৃথিবীর যেকোনো দেশের নাম 
    এবং তার সঠিক ফ্ল্যাগ (Flag) ও ২ অক্ষরের শর্ট নেম (Short Name) বের করার ফাংশন।
    """
    try:
        raw_num = str(number).strip()
        if not raw_num.startswith('+'):
            raw_num = '+' + raw_num
            
        parsed_num = phonenumbers.parse(raw_num, None)
        region_code = phonenumbers.region_code_for_number(parsed_num)
        
        if region_code:
            flag = "".join(chr(ord(c) + 127397) for c in region_code.upper())
            return flag, region_code.upper()
    except:
        pass
    
    return "🌐", "GL"

def detect_language(msg):
    """
    মেসেজের ক্যারেক্টার চেক করে স্বয়ংক্রিয়ভাবে ল্যাঙ্গুয়েজ বা ভাষা ডিটেক্ট করার এআই মেথড।
    """
    msg_lower = msg.lower()
    if re.search(r'[া-ীু-ূে-ো]', msg):
        return "Bangla"
    elif any(word in msg_lower for word in ["code", "otp", "is", "verification", "your"]):
        return "English"
    elif any(word in msg_lower for word in ["код", "подтверждения", "ваш"]):
        return "Russian"
    elif any(word in msg_lower for word in ["g-", "tu", "codigo", "verificacion"]):
        return "Spanish"
    return "English"

def safe_load_json(file_path, default_value):
    if os.path.exists(file_path):
        try:
            if os.path.getsize(file_path) == 0: return default_value
            with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return default_value
    return default_value

def send_to_telegram_group_premium(service, number, otp, full_msg):
    flag, short_name = get_country_info(number)
    lang = detect_language(full_msg)
    
    srv_name = service.lower()
    clean_srv = next((v for k, v in SERVICE_ICONS.items() if k in srv_name), service.upper())
    
    text = (
        f"{flag} <b>{short_name}</b> {clean_srv}\n"
        f"{mask_number(number)} [<b>{lang}</b>]"
    )
    
    payload = {
        "chat_id": OTP_GROUP_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": f"🔑 {otp}", "copy_text": {"text": str(otp)}}],
                [
                    {"text": "🔝 Number", "url": "https://t.me/Premium_SMS2_bot"},
                    {"text": "🤖 Methods", "url": "https://t.me/Earning_Tips055"}
                ]
            ]
        }
    }
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=10)
    except: pass

def send_direct_to_user_inbox(service, number, otp):
    current_users = safe_load_json(USER_FILE, {})
    if not current_users: return

    clean_num = re.sub(r'\D', '', str(number))
    if len(clean_num) < 5: return
    target_part = clean_num[-5:]
    
    flag, short_name = get_country_info(number)

    for uid, u_info in current_users.items():
        if not isinstance(u_info, dict): continue
        active_numbers = u_info.get("active_numbers", [])
        
        for num_obj in active_numbers:
            user_clean_num = re.sub(r'\D', '', num_obj.get("number", ""))
            if target_part in user_clean_num:
                srv_clean = service.upper()
                for k, v in SERVICE_ICONS.items():
                    if k in service.lower():
                        srv_clean = v
                        break
                
                inbox_text = (
                    f"{flag} <b>{short_name}</b> {srv_clean}\n"
                    f"<code>{num_obj['number']}</code>"
                )
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                
                payload = {
                    "chat_id": int(uid),
                    "text": inbox_text,
                    "parse_mode": "HTML",
                    "reply_markup": {
                        "inline_keyboard": [
                            [{"text": f"🔑 {otp}", "copy_text": {"text": str(otp)}}]
                        ]
                    }
                }
                try: requests.post(url, json=payload, timeout=10)
                except: pass
                return

def main():
    print(f"🟢 [Railway Log] {PANEL_NAME} স্ক্যানার রানিং...")
    
    initial_list = safe_load_json(SENT_FILE, [])
    for item in initial_list:
        LOCAL_PROCESSED_KEYS.add(str(item))

    while True:
        try:
            dt1_time = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            params = {"token": API_TOKEN, "dt1": dt1_time, "records": "30"}
            
            res = requests.get(API_BASE_URL, params=params, timeout=15)
            if res.status_code == 200:
                try: records = res.json()
                except: records = []
                
                if isinstance(records, list) and len(records) > 0:
                    new_found = False
                    for row in reversed(records):
                        if len(row) >= 3:
                            srv, num, msg = str(row[0]).strip(), str(row[1]).strip(), str(row[2]).strip()
                            
                            # ওটিপি ডিটেকশন লজিক আপডেট করা হয়েছে
                            otp_match = re.search(r'\b(\d{3,4}[-\s]?\d{3,4})\b', msg)
                            if otp_match:
                                otp = otp_match.group()
                            else:
                                fallback_match = re.search(r'\b(\d{4,8})\b', msg)
                                otp = fallback_match.group() if fallback_match else "N/A"
                            
                            uid_key = f"{num}_{otp}"
                            
                            if uid_key not in LOCAL_PROCESSED_KEYS:
                                LOCAL_PROCESSED_KEYS.add(uid_key) 
                                
                                print(f"🔥 [NEW OTP] Processing {num} -> Country Detected automatically")
                                
                                send_to_telegram_group_premium(srv, num, otp, msg)
                                send_direct_to_user_inbox(srv, num, otp)
                                
                                new_found = True
                    
                    if new_found:
                        try:
                            with open(SENT_FILE, 'w', encoding='utf-8') as f:
                                json.dump(list(LOCAL_PROCESSED_KEYS), f, indent=4)
                        except: pass
            
            time.sleep(2) 
        except Exception as e:
            time.sleep(2)

if __name__ == "__main__":
    main()
        
