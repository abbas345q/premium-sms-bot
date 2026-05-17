import requests
import time
import re
import json
import os
from datetime import datetime, timedelta

# 🔥 মেইন ফাইল (number_bot) থেকে বটের অবজেক্ট ও আইডি শেয়ার করা হচ্ছে
from number_bot import bot, OTP_GROUP_ID, USER_FILE

# === API CONFIGURATION ===
PANEL_NAME = "Premium OTP Panel" 
API_TOKEN = 'RlFTQ0pBUzRiZHhJVIlVioZthlVIaWZdVI-Dg3ODkUmCZHNFWISIig=='
API_BASE_URL = 'http://147.135.212.197/crapi/st/viewstats'

SENT_FILE = 'db_number_panel.json' # প্যানেলের জন্য ওটিপি ট্র্যাকিং ডাটাবেস

# ওটিপি মেসেজ প্রসেস করার জন্য মেইন ফাইল থেকে ফাংশনটি নিয়ে আসা হলো
from number_bot import process_single_otp_message

def main():
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
                                # মেইন বটের ইঞ্জিনে মেসেজটি পুশ করা হলো (যা ১ সেকেন্ডে ইউজারের ইনবক্সে চলে যাবে)
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
    
