import os
import telebot
import yt_dlp
import threading
import time
import json
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "AAVYA ULTIMATE ONLINE 🚀", 200

# --- CONFIG ---
API_TOKEN = os.getenv('BOT_TOKEN')
DEV_CREDIT = "@AAVYAxBOTS"
bot = telebot.TeleBot(API_TOKEN)

# --- DOWNLOAD LOGIC ---
def download_media(url, chat_id, message_id):
    # Pinterest & Spotify Support
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    }

    try:
        start_time = time.time()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Send 'Downloading' update
            bot.edit_message_text("📥 <b>Downloading... Please wait.</b>", chat_id, message_id, parse_mode='HTML')
            
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            res_time = f"{int((time.time() - start_time) * 1000)}ms"

            api_status = {
                "status": "success",
                "code": 200,
                "response_time": res_time,
                "data": {
                    "found": True,
                    "title": info.get('title', 'Media File')[:40],
                    "platform": info.get('extractor_key', 'Universal'),
                },
                "DEVELOPED BY": DEV_CREDIT
            }
            
            json_preview = f"<pre>{json.dumps(api_status, indent=4)}</pre>"
            final_caption = (
                "✅ <b>DOWNLOAD SUCCESSFUL</b>\n\n"
                "🎯 <b>RESPONSE INFO</b>\n"
                f"{json_preview}\n\n"
                f"👤 <b>Developer:</b> <tg-spoiler>{DEV_CREDIT}</tg-spoiler>"
            )
            
            with open(file_path, 'rb') as media:
                # Reaction on Success
                if "spotify" in url.lower():
                    sent = bot.send_audio(chat_id, media, caption=final_caption, parse_mode='HTML')
                else:
                    sent = bot.send_document(chat_id, media, caption=final_caption, parse_mode='HTML')
                
                try:
                    bot.set_message_reaction(chat_id, sent.message_id, reaction=[{"type": "emoji", "emoji": "💯"}])
                except: pass

            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(chat_id, message_id)

    except Exception as e:
        try:
            bot.set_message_reaction(chat_id, message_id, reaction=[{"type": "emoji", "emoji": "😭"}])
        except: pass
        bot.edit_message_text(f"❌ <b>ERROR:</b> Platform not supported or link dead.", chat_id, message_id, parse_mode='HTML')

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    welcome = (
        f"✨ <b>Welcome {message.from_user.first_name}!</b> ✨\n\n"
        f"<blockquote>Main ek Universal Downloader hoon. Spotify, Pinterest, Insta, aur baaki sab chalta hai yahan!</blockquote>\n\n"
        f"💎 <b>Dev:</b> <tg-spoiler>{DEV_CREDIT}</tg-spoiler>"
    )
    bot.reply_to(message, welcome, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('http'))
def handle_links(message):
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, reaction=[{"type": "emoji", "emoji": "🌚"}])
    except: pass
    
    wait = bot.reply_to(message, "⚡ <b>Processing...</b>", parse_mode='HTML')
    threading.Thread(target=download_media, args=(message.text, message.chat.id, wait.message_id)).start()

if __name__ == "__main__":
    if not os.path.exists('downloads'): os.makedirs('downloads')
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.infinity_polling(timeout=90)
