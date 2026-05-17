import os
import threading
import importlib.util
import time
import requests

# আপনার পার্সোনাল আইডি আপডেট মেসেজের জন্য
MY_CHAT_ID = "6781949890"
BOT_TOKEN = "8674480345:AAHCOBHuV7hBQ0d12bhOpf6RgLvg-ceif3Q"

def send_update(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": MY_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def run_panel(file_path):
    script_name = os.path.basename(file_path)
    try:
        spec = importlib.util.spec_from_file_location("module", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'main'):
            module.main()
    except Exception as e:
        send_update(f"❌ <b>এরর:</b> {script_name} ফাইলে সমস্যা হয়েছে!\n⚠️ <code>{str(e)}</code>")

if __name__ == "__main__":
    send_update("🤖 <b>Central Master Bot Online!</b>\nপ্যানেলগুলো চেক করা হচ্ছে...")
    
    # 'panel_' দিয়ে শুরু হওয়া সব ফাইল খুঁজে বের করবে
    panel_files = [f for f in os.listdir('.') if f.startswith('panel_') and f.endswith('.py')]
    
    if not panel_files:
        send_update("⚠️ কোনো প্যানেল ফাইল (panel_*.py) পাওয়া যায়নি!")
    else:
        for file in panel_files:
            t = threading.Thread(target=run_panel, args=(file,))
            t.daemon = True
            t.start()
            time.sleep(2) # সার্ভার লোড কমাতে গ্যাপ
        
        # বটকে সচল রাখা
        while True:
            time.sleep(10)
          
