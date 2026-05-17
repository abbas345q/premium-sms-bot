import threading
import time
import importlib.util
import os

def run_script(file_name):
    print(f"⚙️ [Master] Starting {file_name}...")
    try:
        spec = importlib.util.spec_from_file_location("module", file_name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'main'):
            module.main()
    except Exception as e:
        print(f"❌ [Master] Error in {file_name}: {str(e)}")

if __name__ == "__main__":
    print("🤖 [Master] Starting Central System...")
    
    # ফাইল দুটির নাম লিস্টে ডিফাইন করা হলো
    files_to_run = ["number_bot.py", "panel_number.py"]
    
    threads = []
    for file in files_to_run:
        if os.path.exists(file):
            t = threading.Thread(target=run_script, args=(file,))
            t.daemon = True
            t.start()
            threads.append(t)
            time.sleep(2) # সার্ভার লোড ব্যালেন্স করার জন্য বিরতি
        else:
            print(f"⚠️ [Master] File not found: {file}")
            
    print("🚀 [Master] All background threads are running.")
    
    # মাস্টার প্রসেসকে আজীবন সচল রাখার লুপ
    while True:
        time.sleep(10)
        
