import os, telebot, yt_dlp, threading, time, requests
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "AAVYA DOWNLOADER IS LIVE 🚀", 200

API_TOKEN = os.getenv('BOT_TOKEN')
DEV_CREDIT = "@AAVYAxBOTS"
bot = telebot.TeleBot(API_TOKEN, threaded=True)

# Pinterest Fix: Short URL ko expand karne ke liye
def get_full_url(url):
    try:
        res = requests.get(url, allow_redirects=True, timeout=5)
        return res.url
    except: return url

def download_media(url, chat_id, message_id):
    full_url = get_full_url(url)
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True, 'no_warnings': True,
        'http_headers': {'User-Agent': 'Mozilla/5.0'}
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            bot.edit_message_text("⚡ <b>Downloading...</b>", chat_id, message_id, parse_mode='HTML')
            info = ydl.extract_info(full_url, download=True)
            file_path = ydl.prepare_filename(info)

            caption = (
                "✅ <b>DOWNLOAD SUCCESSFUL</b>\n\n"
                f"🎬 <b>Title:</b> <code>{info.get('title', 'Media')[:50]}</code>\n\n"
                f"💎 <b>Dev:</b> <tg-spoiler>{DEV_CREDIT}</tg-spoiler>"
            )
            
            with open(file_path, 'rb') as media:
                sent = bot.send_document(chat_id, media, caption=caption, parse_mode='HTML')
                # SUCCESS REACTION
                try:
                    bot.set_message_reaction(chat_id, sent.message_id, [telebot.types.ReactionTypeEmoji('💯')], is_big=True)
                except: pass

            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(chat_id, message_id)

    except Exception:
        try:
            bot.set_message_reaction(chat_id, message_id, [telebot.types.ReactionTypeEmoji('😭')])
        except: pass
        bot.edit_message_text("❌ <b>ERROR:</b> Pinterest link failed or not supported.", chat_id, message_id, parse_mode='HTML')

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, f"✨ <b>Welcome!</b>\n\n<blockquote>Send any link to download.</blockquote>\n\n💎 <b>Dev:</b> <tg-spoiler>{DEV_CREDIT}</tg-spoiler>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('http'))
def handle_links(message):
    # RECEIVE REACTION
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [telebot.types.ReactionTypeEmoji('🌚')])
    except: pass
    
    wait = bot.reply_to(message, "⏳ <b>Processing...</b>", parse_mode='HTML')
    threading.Thread(target=download_media, args=(message.text, message.chat.id, wait.message_id)).start()

if __name__ == "__main__":
    if not os.path.exists('downloads'): os.makedirs('downloads')
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.infinity_polling(timeout=90)
