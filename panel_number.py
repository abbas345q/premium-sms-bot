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
SENT_FILE = 'db_number_panel.json'

# ডুপ্লিকেট কানেকশন এড়াতে রান-টাইমে সেফ ইমপোর্ট করা হলো
from number_bot import process_single_otp_message

COUNTRY_MAP = {"263": "🇿🇼 ZW", "964": "🇮🇶 IQ", "880": "🇧🇩 BD", "91": "🇮🇳 IN", "1": "🇺🇸 US", "234": "🇳🇬 NG"}
SERVICE_ICONS = {"facebook": "🔵 Facebook", "whatsapp": "🟢 WhatsApp", "telegram": "✈️ Telegram"}

def mask_number(number):
    num_str = str(number).strip()
    return f"{num_str[:-7]}***{num_str[-4:]}" if len(num_str) > 7 else num_str

def get_flag(number):
    for code, flag in COUNTRY_MAP.items():
        if str(number).startswith(code): return flag
    return "🌐 Global"

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

def main():
    print("--------------------------------------------------")
    print(f"🟢 [Railway Log] {PANEL_NAME} সফলভাবে চালু হয়েছে!")
    print(f"📡 [Railway Log] কোড স্ক্যানিং শুরু... প্রতি ৪ সেকেন্ড পর পর এপিআই চেক করা হচ্ছে।")
    print("--------------------------------------------------")
    
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, 'r') as f:
                content = f.read().strip()
                sent_set = set(json.loads(content)) if content else set()
        except: sent_set = set()
    else: sent_set = set()

    while True:
        try:
            dt1_time = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            params = {"token": API_TOKEN, "dt1": dt1_time, "records": "50"}
            
            res = requests.get(API_BASE_URL, params=params, timeout=25)
            
            if res.status_code == 200:
                records = res.json()
                
                if isinstance(records, list) and len(records) > 0:
                    new_found = False
                    for row in reversed(records):
                        if len(row) >= 3:
                            srv, num, msg = str(row[0]).strip(), str(row[1]).strip(), str(row[2]).strip()
                            uid_key = f"{num}_{msg}"
                            
                            if uid_key not in sent_set:
                                otp_match = re.search(r'\b(\d{4,8})\b', msg)
                                otp = otp_match.group() if otp_match else "N/A"
                                
                                # রেলওয়ে কনসোলে লাইভ ওটিপি ট্র্যাকিং প্রিন্ট
                                print(f"🔥 [Railway Log] New OTP Detected! Service: {srv} | Number: {num}")
                                
                                # ১. মেইন ওটিপি গ্রুপে পুশ হবে
                                send_to_telegram_group_premium(srv, num, otp, msg)
                                
                                # ২. ইউজারের ব্যক্তিগত ইনবক্সে পুশ হবে
                                full_text = f"Service: {srv}\nNumber: {num}\nMsg: {msg}"
                                process_single_otp_message(full_text)
                                
                                sent_set.add(uid_key)
                                new_found = True
                    
                    if new_found:
                        with open(SENT_FILE, 'w') as f:
                            json.dump(list(sent_set), f)
                else:
                    print(f"📡 [Railway Log] চেক করা হয়েছে: প্যানেলে নতুন কোনো ওটিপি নেই।")
            else:
                print(f"❌ [Railway Log] API Error: সার্ভার রেসপন্স কোড {res.status_code}")
            
            time.sleep(4) 
        except Exception as e:
            print(f"⚠️ [Railway Log] লুপে সমস্যা হয়েছে: {str(e)}")
            time.sleep(8)

if __name__ == "__main__":
    main()
    
