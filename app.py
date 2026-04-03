import os, telebot, yt_dlp, threading, time, requests
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "AAVYA OWNER MODE ACTIVE 🚀", 200

# --- CONFIG VARIABLES ---
API_TOKEN = os.getenv('BOT_TOKEN')
# 👇 Yahan apni Numerical ID daalo
OWNER_ID = 12345678  
DEV_CREDIT = "@AAVYAxBOTS"
bot = telebot.TeleBot(API_TOKEN, threaded=True)

# --- HELPERS ---
def is_owner(message):
    return message.from_user.id == OWNER_ID

def get_full_url(url):
    try:
        res = requests.get(url, allow_redirects=True, timeout=5)
        return res.url
    except: return url

# --- OWNER COMMANDS ---
@bot.message_handler(commands=['stats'], func=is_owner)
def send_stats(message):
    status_text = (
        "📊 <b>BOT STATUS REPORT</b>\n\n"
        "<blockquote><b>Status:</b> Running\n"
        "<b>Server:</b> Render\n"
        "<b>Auth:</b> Owner Verified ✅</blockquote>"
    )
    bot.reply_to(message, status_text, parse_mode='HTML')

# --- DOWNLOAD LOGIC ---
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
            bot.edit_message_text("⚡ <b><blockquote>Processing your request...</blockquote></b>", chat_id, message_id, parse_mode='HTML')
            info = ydl.extract_info(full_url, download=True)
            file_path = ydl.prepare_filename(info)

            caption = (
                "✅ <b>DOWNLOAD SUCCESSFUL</b>\n\n"
                f"🎬 <b>Title:</b> <code>{info.get('title', 'Media')[:50]}</code>\n\n"
                f"💎 <b>Developed By:</b> <tg-spoiler>{DEV_CREDIT}</tg-spoiler>"
            )
            
            with open(file_path, 'rb') as media:
                sent = bot.send_document(chat_id, media, caption=caption, parse_mode='HTML')
                try:
                    bot.set_message_reaction(chat_id, sent.message_id, [telebot.types.ReactionTypeEmoji('💯')], is_big=True)
                except: pass

            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(chat_id, message_id)

    except Exception:
        try:
            bot.set_message_reaction(chat_id, message_id, [telebot.types.ReactionTypeEmoji('😭')])
        except: pass
        error_text = "❌ <b>ERROR</b>\n\n<b><blockquote>Pinterest download fail ho gaya. Link public hona zaroori hai!</blockquote></b>"
        bot.edit_message_text(error_text, chat_id, message_id, parse_mode='HTML')

# --- PUBLIC HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    welcome = (
        f"✨ <b>WELCOME {message.from_user.first_name.upper()}!</b> ✨\n\n"
        "<b><blockquote>Main ek powerful downloader hoon. Pinterest, Insta, aur YouTube ke links bhejein!</blockquote></b>\n\n"
        f"💎 <b>Dev:</b> <tg-spoiler>{DEV_CREDIT}</tg-spoiler>"
    )
    bot.reply_to(message, welcome, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('http'))
def handle_links(message):
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [telebot.types.ReactionTypeEmoji('🌚')])
    except: pass
    
    wait_text = "⏳ <b><blockquote>Hold on, fetching your media...</blockquote></b>"
    wait = bot.reply_to(message, wait_text, parse_mode='HTML')
    threading.Thread(target=download_media, args=(message.text, message.chat.id, wait.message_id)).start()

if __name__ == "__main__":
    if not os.path.exists('downloads'): os.makedirs('downloads')
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.infinity_polling(timeout=90)
