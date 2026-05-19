import telebot
import json
import time
import os

API_TOKEN = '7634786660:AAHvY09ndmYnO6pLpz_84rSLqGUEMlfwNd4'
USER_FILE = 'Users_data.json'
QUEUE_FILE = 'broadcast_queue.json'

bot = telebot.TeleBot(API_TOKEN)

print("🚀 Broadcast Notifier Started...")

while True:
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if data and data.get("message"):
                    msg = data["message"]
                    with open(USER_FILE, 'r', encoding='utf-8') as uf:
                        users = json.load(uf)
                    
                    print(f"📢 Sending broadcast to {len(users)} users...")
                    for uid in users.keys():
                        try:
                            bot.send_message(chat_id=int(uid), text=msg, parse_mode="HTML")
                            time.sleep(0.1)
                        except: continue
                    
                    # কাজ শেষে ফাইল খালি করা
                    with open(QUEUE_FILE, 'w') as f:
                        json.dump({"message": ""}, f)
                    print("✅ Broadcast Finished.")
            except: pass
    time.sleep(2)
                  
