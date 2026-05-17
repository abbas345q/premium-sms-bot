import requests
import time
import re
import json
import os
from datetime import datetime, timedelta

# 🔥 মেইন ফাইল (number_bot) থেকে বটের অবজেক্ট, আইডি ও ওটিপি প্রসেসর শেয়ার করা হচ্ছে
from number_bot import bot, OTP_GROUP_ID, USER_FILE, ADMIN_ID, process_single_otp_message

# === API CONFIGURATION ===
PANEL_NAME = "Premium OTP Panel" 
API_TOKEN = 'RlFTQ0pBUzRiZHhJVIlVioZthlVIaWZdVI-Dg3ODkUmCZHNFWISIig=='
API_BASE_URL = 'http://147.135.212.197/crapi/st/viewstats'

SENT_FILE = 'db_number_panel.json' # প্যানেলের জন্য ওটিপি ট্র্যাকিং ডাটাবেস

# আইকন ও দেশ সেটিংস (গ্রুপে প্রিমিয়াম স্টাইলে মেসেজ পাঠানোর জন্য)
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
    """গ্রুপে ওটিপি আসার সাথে সাথে প্রিমিয়াম স্টাইলে ফরওয়ার্ড করার ফাংশন"""
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
    markup = {"inline_keyboard": [[{"text": "🔝 Number", "url": "https://t.me/Premium_SMS2_bot"},{"text": "🤖 Methods", "url": "https://t.me/Earning_Tips055"}]]}
    try:
        bot.send_message(OTP_GROUP_ID, text, parse_mode="HTML", reply_markup=json.dumps(markup))
    except Exception as e:
        print(f"⚠️ গ্রুপে ওটিপি ফরওয়ার্ড করতে ব্যর্থ: {e}")

def main():
    print(f"⚙️ {PANEL_NAME}: মেইন বট রেডি হওয়ার জন্য ৫ সেকেন্ড অপেক্ষা করা হচ্ছে...")
    time.sleep(5) # মেইন বটের কানেকশন স্টেবল হওয়ার জন্য বিরতি
    
    # 🔥 ইনবক্সে কনফার্মেশন মেসেজ পাঠানোর জন্য রিস্টার্ট ট্রাই লুপ
    msg_sent = False
    retry_count = 0
    while not msg_sent and retry_count < 5:
        try:
            bot.send_message(ADMIN_ID, "✅ <b>আপনার বট সফলভাবে চালু হয়েছে এবং কোড স্ক্যানিং শুরু করেছে।</b>", parse_mode="HTML")
            print("🚀 কনফার্মেশন মেসেজ আপনার ইনবক্সে সফলভাবে পাঠানো হয়েছে।")
            msg_sent = True
        except Exception as e:
            retry_count += 1
            print(f"⚠️ মেসেজ পাঠানো যায়নি (চেষ্টা: {retry_count}/5)। কারণ: {e}")
            time.sleep(5) # ৫ সেকেন্ড পর আবার চেষ্টা করবে
            
    print(f"🚀 {PANEL_NAME} রিয়েল-টাইম ওটিপি চেক করার জন্য প্রস্তুত...")
    
    # ডুপ্লিকেট মেসেজ ফিল্টার করার মেমোরি ফাইল লোড করা
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, 'r') as f:
                content = f.read().strip()
                sent_set = set(json.loads(content)) if content else set()
        except: sent_set = set()
    else: sent_set = set()

    while True:
        try:
            # বিগত ১ ঘণ্টার ডেটা রিকোয়েস্ট করার টাইমস্ট্যাম্প
            dt1_time = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            
            params = {
                "token": API_TOKEN,
                "dt1": dt1_time,
                "records": "50"
            }
            
            res = requests.get(API_BASE_URL, params=params, timeout=25)
            
            if res.status_code == 200:
                records = res.json()
                
                if isinstance(records, list) and len(records) > 0:
                    new_found = False
                    for row in reversed(records):
                        if len(row) >= 3:
                            srv, num, msg = str(row[0]).strip(), str(row[1]).strip(), str(row[2]).strip()
                            uid_key = f"{num}_{msg}"
                            
                            # ওটিপিটি আগে পাঠানো না হয়ে থাকলে প্রসেস করবে
                            if uid_key not in sent_set:
                                # মেসেজ থেকে শুধু ওটিপি কোডটি আলাদা করার লজিক
                                otp_match = re.search(r'\b(\d{4,8})\b', msg)
                                otp = otp_match.group() if otp_match else "N/A"
                                
                                # ১. 🔥 ওটিপি পাওয়ার সাথে সাথে আপনার মেইন গ্রুপে প্রিমিয়াম স্টাইলে ফরওয়ার্ড হবে
                                send_to_telegram_group_premium(srv, num, otp, msg)
                                
                                # ২. 🔥 ওটিপি পাওয়ার সাথে সাথে ইউজারের ব্যক্তিগত ইনবক্সেও পুশ হবে
                                full_text = f"Service: {srv}\nNumber: {num}\nMsg: {msg}"
                                process_single_otp_message(full_text)
                                
                                sent_set.add(uid_key)
                                new_found = True
                    
                    if new_found:
                        with open(SENT_FILE, 'w') as f:
                            json.dump(list(sent_set), f)
                else:
                    print(f"📡 {PANEL_NAME}: প্যানেলে নতুন কোনো ওটিপি নেই।")
            else:
                print(f"❌ {PANEL_NAME} Error: সার্ভার রেসপন্স কোড {res.status_code}")

            time.sleep(4) # প্রতি ৪ সেকেন্ড পর পর এপিআই চেক করবে
        except Exception as e:
            print(f"⚠️ {PANEL_NAME} লুপ এরর: {str(e)}")
            time.sleep(8)

if __name__ == "__main__":
    main()
    
