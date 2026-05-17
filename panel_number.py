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

COUNTRY_MAP = {"263": "🇿🇼 ZW", "964": "🇮🇶 IQ", "880": "🇧🇩 BD", "91": "🇮🇳 IN", "1": "🇺🇸 US", "234": "🇳🇬 NG"}
SERVICE_ICONS = {"facebook": "🔵 Facebook", "whatsapp": "🟢 WhatsApp", "telegram": "✈️ Telegram"}

def mask_number(number):
    num_str = str(number).strip()
    return f"{num_str[:-7]}***{num_str[-4:]}" if len(num_str) > 7 else num_str

def get_flag(number):
    for code, flag in COUNTRY_MAP.items():
        if str(number).startswith(code): return flag
    return "🌐 Global"

def safe_load_json(file_path, default_value):
    if os.path.exists(file_path):
        try:
            if os.path.getsize(file_path) == 0: return default_value
            with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return default_value
    return default_value

def send_to_telegram_group_premium(service, number, otp, full_msg):
    """ওটিপি গ্রুপে সুন্দর করে মাত্র ১ বার পোস্ট করার ফাংশন"""
    flag = get_flag(number)
    srv_name = service.lower()
    header = next((v for k, v in SERVICE_ICONS.items() if k in srv_name), f"🔔 {service.upper()}")
    
    text = (
        f"✅ <b>New OTP Received</b>\n\n"
        f"{flag}\n<b>{header}</b>\n\n"
        f"📲 <b>Number:</b> <code>{mask_number(number)}</code>\n\n"
        f"🔑 <b>OTP:</b> <code>{otp}</code>\n\n"
        f"📩 <b>Full Msg:</b>\n"
        f"<pre>{full_msg}</pre>"
    )
    
    payload = {
        "chat_id": OTP_GROUP_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "🔝 Number", "url": "https://t.me/Premium_SMS2_bot"},
                    {"text": "🤖 Methods", "url": "https://t.me/Earning_Tips055"}
                ]
            ]
        }
    }
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=15)
    except: pass

def send_direct_to_user_inbox(service, number, otp):
    """সরাসরি ডাটাবেজ ফাইল চেক করে ইউজারের ইনবক্সে ওটিপি পুশ করার ফাংশন"""
    current_users = safe_load_json(USER_FILE, {})
    if not current_users: return

    clean_num = re.sub(r'\D', '', str(number))
    if len(clean_num) < 5: return
    
    # নম্বরের শেষ ৫টি ডিজিট দিয়ে ইউজারের একটিভ লিস্ট চেক করা হচ্ছে
    target_part = clean_num[-5:]
    
    for uid, u_info in current_users.items():
        if not isinstance(u_info, dict): continue
        active_numbers = u_info.get("active_numbers", [])
        
        for num_obj in active_numbers:
            user_clean_num = re.sub(r'\D', '', num_obj.get("number", ""))
            if target_part in user_clean_num:
                
                # সার্ভিস আইকন ডিটেকশন
                srv_clean = service.upper()
                for k, v in SERVICE_ICONS.items():
                    if k in service.lower():
                        srv_clean = v
                        break
                        
                final_msg = (
                    f"✨ **NEW OTP RECEIVED!**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Service:** {srv_clean}\n"
                    f"🔢 **Number:** `{num_obj['number']}`\n"
                    f"🔑 **OTP Code:** `{otp}`\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {"chat_id": int(uid), "text": final_msg, "parse_mode": "Markdown"}
                try: 
                    requests.post(url, json=payload, timeout=10)
                except: 
                    pass
                return

def main():
    print("--------------------------------------------------")
    print(f"🟢 [Railway Log] {PANEL_NAME} সফলভাবে চালু হয়েছে!")
    print(f"📡 [Railway Log] কোড স্ক্যানিং শুরু... প্রতি ৪ সেকেন্ড পর পর এপিআই চেক করা হচ্ছে।")
    print("--------------------------------------------------")
    
    initial_list = safe_load_json(SENT_FILE, [])
    sent_set = set(initial_list)

    while True:
        try:
            dt1_time = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            params = {"token": API_TOKEN, "dt1": dt1_time, "records": "50"}
            
            res = requests.get(API_BASE_URL, params=params, timeout=25)
            
            if res.status_code == 200:
                try:
                    records = res.json()
                except:
                    time.sleep(5)
                    continue
                
                if isinstance(records, list) and len(records) > 0:
                    new_found = False
                    for row in reversed(records):
                        if len(row) >= 3:
                            srv, num, msg = str(row[0]).strip(), str(row[1]).strip(), str(row[2]).strip()
                            uid_key = f"{num}_{msg}"
                            
                            if uid_key not in sent_set:
                                otp_match = re.search(r'\b(\d{4,8})\b', msg)
                                otp = otp_match.group() if otp_match else "N/A"
                                
                                print(f"🔥 [Railway Log] New OTP Detected! Service: {srv} | Number: {num}")
                                
                                # ১. গ্রুপে ১ বার পাঠানো হচ্ছে
                                send_to_telegram_group_premium(srv, num, otp, msg)
                                
                                # ২. সরাসরি ইউজারের ইনবক্সে ১ বার পাঠানো হচ্ছে (গ্রুপের মেসেজের ওপর নির্ভর না করে)
                                send_direct_to_user_inbox(srv, num, otp)
                                
                                sent_set.add(uid_key)
                                new_found = True
                    
                    if new_found:
                        try:
                            with open(SENT_FILE, 'w', encoding='utf-8') as f:
                                json.dump(list(sent_set), f, indent=4)
                        except: pass
            
            time.sleep(4) 
        except Exception as e:
            time.sleep(6)

if __name__ == "__main__":
    main()
                            
