import requests
import time
import re
import json
import os
from datetime import datetime, timedelta

# === API CONFIGURATION ===
PANEL_NAME = "Number Panel" # প্যানেলের নাম আইডেন্টিফাই করার জন্য
API_TOKEN = 'RlFTQ0pBUzRiZHhJVIlVioZthlVIaWZdVI-Dg3ODkUmCZHNFWISIig=='
API_BASE_URL = 'http://147.135.212.197/crapi/st/viewstats'

BOT_TOKEN = '8674480345:AAHCOBHuV7hBQ0d12bhOpf6RgLvg-ceif3Q'
GROUP_CHAT_ID = '-1002295608331' # মেইন গ্রুপ আইডি
MY_CHAT_ID = '6781949890'      # আপনার পার্সোনাল আইডি

# আপনার মেইন বটের টোকেন (যা দিয়ে গ্রাহক ইনবক্সে ওটিপি পাবে)
MAIN_BOT_TOKEN = '7634786660:AAHvY09ndmYnO6pLpz_84rSLqGUEMlfwNd4'
USER_DATA_FILE = 'users_data.json'

SENT_FILE = 'db_number_panel.json' # এই প্যানেলের জন্য আলাদা ডাটাবেস ফাইল

# আইকন সেটিংস
COUNTRY_MAP = {"263": "🇿🇼 ZW", "964": "🇮🇶 IQ", "880": "🇧🇩 BD", "91": "🇮🇳 IN", "1": "🇺🇸 US", "234": "🇳🇬 NG"}
SERVICE_ICONS = {"facebook": "🔵 Facebook", "whatsapp": "🟢 WhatsApp", "telegram": "✈️ Telegram"}

def mask_number(number):
    num_str = str(number).strip()
    return f"{num_str[:-7]}***{num_str[-4:]}" if len(num_str) > 7 else num_str

def get_flag(number):
    for code, flag in COUNTRY_MAP.items():
        if str(number).startswith(code): return flag
    return "🌐 Global"

def send_update_to_me(message):
    """আপনার পার্সোনাল ইনবক্সে লগইন স্ট্যাটাস বা এরর পাঠানোর ফাংশন"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": MY_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def forward_to_user_directly(number, otp_code, service_name):
    """গ্রুপের বাটন ব্লকিং সম্পূর্ণ বাইপাস করে গ্রাহককে সরাসরি ইনবক্স করার ফাংশন"""
    if not os.path.exists(USER_DATA_FILE):
        return
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            current_users = json.load(f)
    except:
        return

    clean_incoming_num = re.sub(r'\D', '', str(number))
    if len(clean_incoming_num) < 4: return
    incoming_last_4 = clean_incoming_num[-4:]

    for uid, u_info in current_users.items():
        active_numbers = u_info.get("active_numbers", [])
        for num_obj in active_numbers:
            clean_user_num = re.sub(r'\D', '', num_obj["number"])
            if len(clean_user_num) < 4: continue
            user_last_4 = clean_user_num[-4:]
            
            # নাম্বারের শেষ ৪ ডিজিট ম্যাচ করলে সরাসরি মেইন বটের মাধ্যমে কাস্টমারকে ইনবক্স করবে
            if user_last_4 == incoming_last_4:
                final_msg = (
                    f"✨ **NEW OTP RECEIVED!**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📱 **Service:** {service_name.upper()}\n"
                    f"🔢 **Number:** `{num_obj['number']}`\n"
                    f"🔑 **OTP Code:** `{otp_code}`\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                url = f"https://api.telegram.org/bot{MAIN_BOT_TOKEN}/sendMessage"
                try:
                    requests.post(url, json={"chat_id": int(uid), "text": final_msg, "parse_mode": "Markdown"}, timeout=10)
                except:
                    pass
                return

def send_to_telegram_premium(service, number, otp, full_msg):
    """গ্রুপে প্রিমিয়াম স্টাইলে ওটিপি পাঠানোর ফাংশন"""
    flag = get_flag(number)
    srv_name = service.lower()
    header = next((v for k, v in SERVICE_ICONS.items() if k in srv_name), f"🔔 {service.upper()}")
    
    text = (
        f"✅ New OTP Received\n\n"
        f"{flag}\n<b>{header}</b>\n\n"
        f"📲 <b>Number:</b> <code>{mask_number(number)}</code>\n\n"
        f"🔑 <b>OTP:</b> <code>{otp}</code>\n\n"
        f"📩 <b>Full Msg:</b>\n"
        f"<pre>{full_msg}</pre>"
    )
    markup = {"inline_keyboard": [[{"text": "🔝 Number", "url": "https://t.me/Premium_SMS2_bot"},{"text": "🤖 Methods", "url": "https://t.me/Earning_Tips055"}]]}
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": GROUP_CHAT_ID, "text": text, "parse_mode": "HTML", "reply_markup": json.dumps(markup)}, timeout=15)
    except: pass

def main():
    # মাস্টার বট রান হলে ইনবক্সে রিপোর্ট দিবে
    send_update_to_me(f"✅ <b>{PANEL_NAME}:</b> মনিটরিং শুরু হয়েছে। প্যানেল ডাটা রিড করা হচ্ছে...")
    
    print(f"🚀 {PANEL_NAME} নতুন ওটিপি চেক করার জন্য প্রস্তুত...")
    
    # মেমোরি ফাইল লোড করা
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
                            uid = f"{num}_{msg}"
                            
                            if uid not in sent_set:
                                otp_match = re.search(r'\b(\d{4,8})\b', msg)
                                otp = otp_match.group() if otp_match else "N/A"
                                
                                # ১. গ্রুপে প্রিমিয়াম স্টাইলে বাটনসহ মেসেজ পাঠাবে
                                send_to_telegram_premium(srv, num, otp, msg)
                                
                                # ২. 🔥 গ্রুপ ব্লকিং বাইপাস করে সরাসরি ইউজারের ইনবক্সে মেইন বট দিয়ে ওটিপি পুশ করবে
                                forward_to_user_directly(num, otp, srv)
                                
                                sent_set.add(uid)
                                new_found = True
                    
                    if new_found:
                        with open(SENT_FILE, 'w') as f:
                            json.dump(list(sent_set), f)
                else:
                    print(f"📡 {PANEL_NAME}: নতুন কোনো ওটিপি নেই।")
            else:
                send_update_to_me(f"❌ <b>{PANEL_NAME} Error:</b> সার্ভার রেসপন্স করছে না। (Status: {res.status_code})")

            time.sleep(4) 
        except Exception as e:
            send_update_to_me(f"⚠️ <b>{PANEL_NAME} এরর:</b> {str(e)}")
            time.sleep(8)

if __name__ == "__main__":
    main()
                  
