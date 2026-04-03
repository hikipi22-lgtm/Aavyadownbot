import os
import telebot
import yt_dlp
import threading
import time
import json
from flask import Flask

# Flask setup for Render
app = Flask(__name__)
@app.route('/')
def home(): return "AAVYA DOWNLOADER IS LIVE 🚀", 200

# CONFIGURATION
# Render Settings -> Environment mein 'BOT_TOKEN' hona chahiye
API_TOKEN = os.getenv('BOT_TOKEN')
DEV_CREDIT = "@AAVYAxBOTS"
bot = telebot.TeleBot(API_TOKEN)

# MEDIA DOWNLOAD LOGIC
def download_media(url, chat_id, message_id):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
    }

    try:
        start_time = time.time()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            res_time = f"{int((time.time() - start_time) * 1000)}ms"

            # Neat JSON Status
            api_status = {
                "status": "success",
                "code": 200,
                "response_time": res_time,
                "data": {
                    "found": True,
                    "title": info.get('title', 'Media File')[:50] + "...",
                    "platform": info.get('extractor_key', 'Social Media'),
                },
                "DEVELOPED BY": DEV_CREDIT
            }
            
            json_preview = f"<pre>{json.dumps(api_status, indent=4)}</pre>"
            
            final_caption = (
                "✅ <b>DOWNLOAD SUCCESSFUL</b>\n\n"
                "🎯 <b>RESPONSE INFO</b>\n"
                f"{json_preview}\n\n"
                f"👤 <b>Developer:</b> {DEV_CREDIT}"
            )
            
            with open(file_path, 'rb') as media:
                # Send Media
                sent_msg = bot.send_document(chat_id, media, caption=final_caption, parse_mode='HTML')
                # 💯 Reaction on Success
                try:
                    bot.set_message_reaction(chat_id, sent_msg.message_id, reaction=[{"type": "emoji", "emoji": "💯"}])
                except: pass

            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(chat_id, message_id)

    except Exception as e:
        # 😭 Reaction on Failure
        try:
            bot.set_message_reaction(chat_id, message_id, reaction=[{"type": "emoji", "emoji": "😭"}])
        except: pass
        bot.edit_message_text(f"❌ <b>Error:</b> Link not supported or file too large.", chat_id, message_id, parse_mode='HTML')

# HANDLERS
@bot.message_handler(commands=['start'])
def start(message):
    welcome = (
        f"👋 <b>Welcome {message.from_user.first_name}!</b>\n\n"
        f"Kishi bhi Video ya Photo ka link bhejein.\n\n"
        f"💎 <b>Dev:</b> {DEV_CREDIT}"
    )
    bot.reply_to(message, welcome, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('http'))
def handle_links(message):
    # 🌚 Reaction on getting link
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, reaction=[{"type": "emoji", "emoji": "🌚"}])
    except: pass
    
    wait = bot.reply_to(message, "⚡ <b>Processing your request...</b>", parse_mode='HTML')
    threading.Thread(target=download_media, args=(message.text, message.chat.id, wait.message_id)).start()

if __name__ == "__main__":
    if not os.path.exists('downloads'): os.makedirs('downloads')
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    while True:
        try:
            bot.infinity_polling(timeout=90)
        except Exception:
            time.sleep(10)
