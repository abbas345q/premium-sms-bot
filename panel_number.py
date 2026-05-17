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
    """ফাইল খালি বা ড্যামেজ থাকলে সেটিকে ক্র্যাশ না করিয়ে নিরাপদে রিকভার করার ফাংশন"""
    if os.path.exists(file_path):
        try:
            if os.path.getsize(file_path) == 0:
                return default_value
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default_value
    return default_value

def send_to_telegram_group_premium(service, number, otp, full_msg):
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
    except Exception as e:
        print(f"⚠️ [Railway Log] গ্রুপে ওটিপি ফরওয়ার্ড করতে ব্যর্থ: {e}")

def process_and_send_to_user_direct(srv, num, msg, otp):
    current_users = safe_load_json(USER_FILE, {})
    if not current_users: return

    clean_txt = re.sub(r'[\s\-\+\(\):,]', '', f"{srv}{num}{msg}")
    
    for uid, u_info in current_users.items():
        if not isinstance(u_info, dict): continue
        active_numbers = u_info.get("active_numbers", [])
        for num_obj in active_numbers:
            clean_num = re.sub(r'\D', '', num_obj["number"])
            if len(clean_num) < 4: continue
            
            if clean_num[-4:] in clean_txt:
                final_msg = (
                    f"✨ *NEW OTP RECEIVED!*\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📱 *Service:* {srv}\n"
                    f"🔢 *Number:* `{num_obj['number']}`\n"
                    f"🔑 *OTP Code:* `{otp}`\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {"chat_id": int(uid), "text": final_msg, "parse_mode": "Markdown"}
                try: requests.post(url, json=payload, timeout=10)
                except: pass
                return

def main():
    print("--------------------------------------------------")
    print(f"🟢 [Railway Log] {PANEL_NAME} সফলভাবে চালু হয়েছে!")
    print(f"📡 [Railway Log] কোড স্ক্যানিং শুরু... প্রতি ৪ সেকেন্ড পর পর এপিআই চেক করা হচ্ছে।")
    print("--------------------------------------------------")
    
    # সুরক্ষিতভাবে পুরনো হিস্ট্রি লোড করা হচ্ছে
    initial_list = safe_load_json(SENT_FILE, [])
    sent_set = set(initial_list)

    while True:
        try:
            dt1_time = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            params = {"token": API_TOKEN, "dt1": dt1_time, "records": "50"}
            
            res = requests.get(API_BASE_URL, params=params, timeout=25)
            
            if res.status_code == 200:
                # এপিআই যদি কোনো কারণে JSON না দিয়ে টেক্সট/এরর পেজ দেয়, তা এখানে হ্যান্ডেল হবে
                try:
                    records = res.json()
                except:
                    print("⚠️ [Railway Log] API থেকে বৈধ JSON ডাটা আসেনি। রিট্রাই করা হচ্ছে...")
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
                                
                                # ১. গ্রুপে ফরওয়ার্ড
                                send_to_telegram_group_premium(srv, num, otp, msg)
                                
                                # ২. ইউজারের ইনবক্সে পুশ
                                process_and_send_to_user_direct(srv, num, msg, otp)
                                
                                sent_set.add(uid_key)
                                new_found = True
                    
                    if new_found:
                        try:
                            with open(SENT_FILE, 'w', encoding='utf-8') as f:
                                json.dump(list(sent_set), f, indent=4)
                        except: pass
                else:
                    pass # কোনো নতুন ওটিপি না থাকলে লগকে ক্লিন রাখার জন্য প্রিন্ট বন্ধ রাখা হলো
            else:
                print(f"❌ [Railway Log] API Error: সার্ভার রেসপন্স কোড {res.status_code}")
            
            time.sleep(4) 
        except Exception as e:
            print(f"⚠️ [Railway Log] লুপে সমস্যা হয়েছে: {str(e)}")
            time.sleep(6)

if __name__ == "__main__":
    main()
    
