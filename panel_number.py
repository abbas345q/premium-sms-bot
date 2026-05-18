import requests
import time
import re
import json
import os
from datetime import datetime, timedelta

# === CONFIGURATION ===
PANEL_NAME = "Premium OTP Panel" 
API_TOKEN = 'RlFTQ0pBUzRiZHhJVIlVioZthlVIaWZdVI-Dg3ODkUmCZHNFWISIig=='
API_BASE_URL = 'http://147.135.212.197/crapi/st/viewstats'

BOT_TOKEN = '7634786660:AAHvY09ndmYnO6pLpz_84rSLqGUEMlfwNd4'
OTP_GROUP_ID = -1002295608331
USER_FILE = 'users_data.json'
SENT_FILE = 'db_number_panel.json'

# কান্ট্রি ডাটাবেস (ফ্ল্যাগ এবং পূর্ণ নাম সহ)
COUNTRY_MAP = {
    "263": ("🇿🇼", "Zimbabwe"),
    "964": ("🇮🇶", "Iraq"),
    "880": ("🇧🇩", "Bangladesh"),
    "91":  ("🇮🇳", "India"),
    "1":   ("🇺🇸", "USA"),
    "234": ("🇳🇬", "Nigeria"),
    "7":   ("🇷🇺", "Russia"),
    "44":  ("🇬🇧", "United Kingdom")
}
SERVICE_ICONS = {"facebook": "🔵 Facebook", "whatsapp": "🟢 WhatsApp", "telegram": "✈️ Telegram"}

# মেমরি লক (ওটিপি ডাবল হওয়া প্রতিরোধ করার জন্য)
LOCAL_PROCESSED_KEYS = set()

def mask_number(number):
    num_str = str(number).strip()
    return f"{num_str[:-7]}***{num_str[-4:]}" if len(num_str) > 7 else num_str

def get_country_info(number):
    """নম্বর থেকে দেশের ফ্ল্যাগ এবং নাম বের করার ফাংশন"""
    clean_num = str(number).lstrip('+').strip()
    # দীর্ঘতম কান্ট্রি কোডগুলো আগে চেক করা হচ্ছে
    for code, info in sorted(COUNTRY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if clean_num.startswith(code):
            return info[0], info[1] # ফ্ল্যাগ, নাম ফেরত দেবে
    return "🌐", "Global"

def safe_load_json(file_path, default_value):
    if os.path.exists(file_path):
        try:
            if os.path.getsize(file_path) == 0: return default_value
            with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return default_value
    return default_value

def send_to_telegram_group_premium(service, number, otp, full_msg):
    # ফ্ল্যাগ এবং দেশের নাম বের করা হচ্ছে
    flag, country_name = get_country_info(number)
    
    srv_name = service.lower()
    header = next((v for k, v in SERVICE_ICONS.items() if k in srv_name), f"🔔 {service.upper()}")
    
    # গ্রুপ মেসেজ ফরম্যাট
    text = (
        f"✅ <b>New OTP Received</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌍 <b>Country:</b> {flag} {country_name}\n\n"
        f"📱 <b>Service:</b> {header}\n\n"
        f"📲 <b>Number:</b> <code>{mask_number(number)}</code>\n\n"
        f"🔑 <b>OTP Code:</b> <code>{otp}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📩 <b>Full Msg:</b>\n"
        f"<pre>{full_msg}</pre>"
    )
    
    payload = {
        "chat_id": OTP_GROUP_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "🔝 Number", "url": "https://t.me/Premium_SMS2_bot"},
                {"text": "🤖 Methods", "url": "https://t.me/Earning_Tips055"}
            ]]
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
    
    # ফ্ল্যাগ এবং দেশের নাম বের করা হচ্ছে
    flag, country_name = get_country_info(number)

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
                
                # ইনবক্স মেসেজ ফরম্যাট (এখানেও কান্ট্রি নাম ও ফ্ল্যাগ যুক্ত করা হয়েছে)
                final_msg = (
                    f"✨ **NEW OTP RECEIVED!**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🌍 **Country:** {flag} {country_name}\n"
                    f"📱 **Service:** {srv_clean}\n"
                    f"🔢 **Number:** `{num_obj['number']}`\n"
                    f"🔑 **OTP Code:** `{otp}`\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {"chat_id": int(uid), "text": final_msg, "parse_mode": "Markdown"}
                try: requests.post(url, json=payload, timeout=10)
                except: pass
                return

def main():
    print(f"🟢 [Railway Log] {PANEL_NAME} স্ক্যানার রানিং...")
    
    # পূর্বের পাঠানো ওটিপি মেমরিতে লোড করা হচ্ছে
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
                            
                            otp_match = re.search(r'\b(\d{4,8})\b', msg)
                            otp = otp_match.group() if otp_match else "N/A"
                            
                            # ডুপ্লিকেট চেক আইডি
                            uid_key = f"{num}_{otp}"
                            
                            if uid_key not in LOCAL_PROCESSED_KEYS:
                                LOCAL_PROCESSED_KEYS.add(uid_key) # সাথে সাথে মেমরি লক
                                
                                print(f"🔥 [NEW OTP] Processing {num} -> OTP: {otp}")
                                
                                # গ্রুপে পাঠানো হচ্ছে 
                                send_to_telegram_group_premium(srv, num, otp, msg)
                                
                                # ইউজারের ইনবক্সে পুশ করা হচ্ছে
                                send_direct_to_user_inbox(srv, num, otp)
                                
                                new_found = True
                    
                    if new_found:
                        try:
                            with open(SENT_FILE, 'w', encoding='utf-8') as f:
                                json.dump(list(LOCAL_PROCESSED_KEYS), f, indent=4)
                        except: pass
            
            time.sleep(3) 
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    main()
    
