import os
import telebot
import yt_dlp
import threading
import time
import json
from flask import Flask
from telebot import apihelper

# --- NETWORK FIX ---
apihelper.SESSION_TIME_OUT = 120
apihelper.RETRY_ON_ERROR = True

app = Flask(__name__)
@app.route('/')
def home(): return "BOT IS LIVE 🚀", 200

# --- CONFIG ---
# Render/Hugging Face ki Settings mein 'BOT_TOKEN' secret daalein
API_TOKEN = os.getenv('BOT_TOKEN')
DEV_CREDIT = "@rajfflive"
bot = telebot.TeleBot(API_TOKEN)

# --- DOWNLOAD LOGIC ---
def download_media(url, chat_id, message_id):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        start_time = time.time()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            res_time = f"{int((time.time() - start_time) * 1000)}ms"

            # JSON Look for the response
            api_status = {
                "status": "success",
                "code": 200,
                "response_time": res_time,
                "data": {
                    "found": True,
                    "title": info.get('title', 'Video'),
                    "platform": info.get('extractor', 'Social Media'),
                },
                "DEVELOPED BY": DEV_CREDIT
            }
            
            json_preview = f"<code>{json.dumps(api_status, indent=4)}</code>"
            
            with open(file_path, 'rb') as media:
                bot.send_video(
                    chat_id, 
                    media, 
                    caption=f"<b>✅ DOWNLOAD SUCCESS</b>\n\n{json_preview}\n\n👤 <b>Dev:</b> {DEV_CREDIT}", 
                    parse_mode='HTML'
                )

            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(chat_id, message_id)

    except Exception:
        bot.edit_message_text(f"❌ <b>Error:</b> Link not supported.", chat_id, message_id, parse_mode='HTML')

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, f"<b>👋 Welcome!</b>\nSend any video link.\n\n💎 <b>Dev:</b> {DEV_CREDIT}", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('http'))
def handle_links(message):
    wait = bot.reply_to(message, "⚡ <b>Processing...</b>", parse_mode='HTML')
    threading.Thread(target=download_media, args=(message.text, message.chat.id, wait.message_id)).start()

if __name__ == "__main__":
    if not os.path.exists('downloads'): os.makedirs('downloads')
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=7860), daemon=True).start()
    
    while True:
        try:
            bot.infinity_polling(timeout=90)
        except:
            time.sleep(10)
