import os, telebot, yt_dlp, threading, time
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "AAVYA DOWNLOADER ACTIVE 🚀", 200

# --- CONFIG ---
API_TOKEN = os.getenv('BOT_TOKEN')
DEV_CREDIT = "@AAVYAxBOTS"
bot = telebot.TeleBot(API_TOKEN)

# --- DOWNLOAD LOGIC ---
def download_media(url, chat_id, message_id):
    # Pinterest Images & Video Bypass
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            bot.edit_message_text("⚡ <b>Downloading... Please wait.</b>", chat_id, message_id, parse_mode='HTML')
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            # Caption without JSON block as requested
            clean_caption = (
                "✅ <b>DOWNLOAD SUCCESSFUL</b>\n\n"
                f"🎬 <b>Title:</b> <code>{info.get('title', 'Media File')[:50]}</code>\n\n"
                f"💎 <b>Developed By:</b> <tg-spoiler>{DEV_CREDIT}</tg-spoiler>"
            )
            
            with open(file_path, 'rb') as media:
                # Success Reaction
                sent = bot.send_document(chat_id, media, caption=clean_caption, parse_mode='HTML')
                try:
                    # New Reaction Logic
                    bot.set_message_reaction(chat_id, sent.message_id, reaction=[{"type": "emoji", "emoji": "💯"}])
                except: pass

            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(chat_id, message_id)

    except Exception:
        try:
            bot.set_message_reaction(chat_id, message_id, reaction=[{"type": "emoji", "emoji": "😭"}])
        except: pass
        bot.edit_message_text("❌ <b>ERROR:</b> Pinterest image/video download failed. Make sure link is public.", chat_id, message_id, parse_mode='HTML')

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = (
        f"✨ <b>Welcome {message.from_user.first_name}!</b> ✨\n\n"
        f"<blockquote>Pinterest, Insta, FB, YT — Sab kuch download hoga!</blockquote>\n\n"
        f"💎 <b>Dev:</b> <tg-spoiler>{DEV_CREDIT}</tg-spoiler>"
    )
    bot.reply_to(message, welcome_text, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('http'))
def handle_links(message):
    # Immediate Reaction on link receipt
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, reaction=[{"type": "emoji", "emoji": "🌚"}])
    except: pass
    
    wait = bot.reply_to(message, "⏳ <b>Processing...</b>", parse_mode='HTML')
    threading.Thread(target=download_media, args=(message.text, message.chat.id, wait.message_id)).start()

if __name__ == "__main__":
    if not os.path.exists('downloads'): os.makedirs('downloads')
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    # Conflict avoid karne ke liye polling settings
    bot.infinity_polling(timeout=90, long_polling_timeout=5)
