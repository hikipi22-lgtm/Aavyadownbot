import os, telebot, yt_dlp, threading, time, requests
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "AAVYA V3 ADMIN ONLINE 🚀", 200

# --- CONFIG VARIABLES ---
API_TOKEN = os.getenv('BOT_TOKEN')
# 👇 Yahan apni numerical ID dalo (e.g., 68453210)
OWNER_ID = 12345678  
DEV_CREDIT = "@AAVYAxBOTS"

bot = telebot.TeleBot(API_TOKEN, threaded=True)

# --- ADMIN DECORATOR ---
def is_owner(message):
    return message.from_user.id == OWNER_ID

# Pinterest Link Expander
def get_full_url(url):
    try:
        res = requests.get(url, allow_redirects=True, timeout=5)
        return res.url
    except: return url

# --- DOWNLOADER ENGINE ---
def download_media(url, chat_id, message_id):
    full_url = get_full_url(url)
    
    # Check if it's Spotify
    is_audio = "spotify" in url.lower()
    
    ydl_opts = {
        'format': 'bestaudio/best' if is_audio else 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True, 
        'no_warnings': True,
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            bot.edit_message_text("⚡ <b><blockquote>Downloading... Please wait a moment.</blockquote></b>", chat_id, message_id, parse_mode='HTML')
            info = ydl.extract_info(full_url, download=True)
            file_path = ydl.prepare_filename(info)

            # Clean Caption
            caption = (
                "✅ <b>DOWNLOAD SUCCESSFUL</b>\n\n"
                f"🎬 <b>Title:</b> <code>{info.get('title', 'Media')[:50]}</code>\n\n"
                f"💎 <b>Developed By:</b> <tg-spoiler>{DEV_CREDIT}</tg-spoiler>"
            )
            
            with open(file_path, 'rb') as media:
                if is_audio:
                    sent = bot.send_audio(chat_id, media, caption=caption, parse_mode='HTML')
                else:
                    sent = bot.send_document(chat_id, media, caption=caption, parse_mode='HTML')
                
                # 💯 Success Reaction
                try:
                    bot.set_message_reaction(chat_id, sent.message_id, [telebot.types.ReactionTypeEmoji('💯')], is_big=True)
                except: pass

            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(chat_id, message_id)

    except Exception:
        try:
            bot.set_message_reaction(chat_id, message_id, [telebot.types.ReactionTypeEmoji('😭')])
        except: pass
        error_msg = "❌ <b>ERROR</b>\n\n<b><blockquote>Download fail ho gaya. Link private ho sakta hai ya platform supported nahi hai.</blockquote></b>"
        bot.edit_message_text(error_msg, chat_id, message_id, parse_mode='HTML')

# --- ADMIN FEATURES ---
@bot.message_handler(commands=['stats'], func=is_owner)
def admin_stats(message):
    stats_text = (
        "📊 <b>ADMIN PANEL</b>\n\n"
        "<b><blockquote>Status: Active\n"
        "Server: Render (V3)\n"
        "Auth: Owner Verified ✅\n"
        "Features: Pinterest Fix + Spotify + Reactions</blockquote></b>"
    )
    bot.reply_to(message, stats_text, parse_mode='HTML')

@bot.message_handler(commands=['broadcast'], func=is_owner)
def admin_broadcast(message):
    bot.reply_to(message, "📢 <b><blockquote>Broadcast feature is ready. (Database connection pending).</blockquote></b>", parse_mode='HTML')

# --- PUBLIC COMMANDS ---
@bot.message_handler(commands=['start'])
def start(message):
    welcome = (
        f"✨ <b>WELCOME {message.from_user.first_name.upper()}!</b> ✨\n\n"
        "<b><blockquote>Main ek Advanced Downloader hoon. Pinterest, Spotify, Insta, YT sab chalta hai!</blockquote></b>\n\n"
        f"💎 <b>Dev:</b> <tg-spoiler>{DEV_CREDIT}</tg-spoiler>"
    )
    bot.reply_to(message, welcome, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('http'))
def handle_links(message):
    # 🌚 Immediate Reaction
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [telebot.types.ReactionTypeEmoji('🌚')])
    except: pass
    
    wait_text = "⏳ <b><blockquote>Processing your link...</blockquote></b>"
    wait = bot.reply_to(message, wait_text, parse_mode='HTML')
    threading.Thread(target=download_media, args=(message.text, message.chat.id, wait.message_id)).start()

if __name__ == "__main__":
    if not os.path.exists('downloads'): os.makedirs('downloads')
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    # Conflict clear karne ke liye skip_pending=True
    bot.infinity_polling(timeout=90, skip_pending=True)
