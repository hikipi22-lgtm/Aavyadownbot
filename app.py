import os
import telebot
import yt_dlp
import threading
import time
import sqlite3
from flask import Flask

# -------------------- FLASK (Render Live) --------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "AAVYA V4 DATABASE ACTIVE 🚀", 200

# -------------------- CONFIGURATION --------------------
API_TOKEN = os.getenv('BOT_TOKEN')
if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable not set!")

OWNER_ID = int(os.getenv('OWNER_ID', '12345678'))  # Apna Telegram ID yahan daalo
DEV_CREDIT = "@AAVYAxBOTS"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 🍪 COOKIES FILE (Instagram fix)
COOKIES_FILE = "cookies.txt"  # Render pe Secret File ka naam same hona chahiye

bot = telebot.TeleBot(API_TOKEN, threaded=True)

# -------------------- DATABASE --------------------
def init_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# -------------------- DOWNLOADER --------------------
def download_media(url, message):
    msg = bot.reply_to(message, "⏳ <b>Downloading...</b>", parse_mode='HTML')

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'user_agent': USER_AGENT,
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,  # 🍪 COOKIE APPLY
        'retries': 5,
        'fragment_retries': 5,
        'extractor_retries': 3,
        'skip_unavailable_fragments': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if 'entries' in info:  # Playlist ka pehla item
                info = info['entries'][0]
                filename = ydl.prepare_filename(info)

            with open(filename, 'rb') as f:
                caption = (
                    "✅ <b>Downloaded Successfully!</b>\n\n"
                    f"<b>💎 Dev: <tg-spoiler>{DEV_CREDIT}</tg-spoiler></b>"
                )
                ext = os.path.splitext(filename)[1].lower()
                if ext in ['.mp4', '.mkv', '.webm', '.avi']:
                    bot.send_video(message.chat.id, f, caption=caption, parse_mode='HTML',
                                   reply_to_message_id=message.message_id)
                elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    bot.send_photo(message.chat.id, f, caption=caption, parse_mode='HTML',
                                   reply_to_message_id=message.message_id)
                else:
                    bot.send_document(message.chat.id, f, caption=caption, parse_mode='HTML',
                                      reply_to_message_id=message.message_id)

            os.remove(filename)
            bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        error_str = str(e)
        if "instagram" in url.lower() and ("login" in error_str.lower() or "429" in error_str):
            reply = (
                "❌ <b>Instagram login required.</b>\n\n"
                "👉 Upload <code>cookies.txt</code> file on Render (Secret Files).\n"
                "⚡ YouTube, TikTok, etc. will still work."
            )
        else:
            reply = f"❌ <b>Error:</b> <code>{error_str[:200]}</code>"
        bot.edit_message_text(reply, message.chat.id, msg.message_id, parse_mode='HTML')

# -------------------- BROADCAST (Admin) --------------------
@bot.message_handler(commands=['broadcast'], func=lambda m: m.from_user.id == OWNER_ID)
def broadcast_command(message):
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        bot.reply_to(message, "Message toh likho!")
        return

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()

    sent = 0
    for user in users:
        try:
            bot.send_message(user[0], f"📢 <b>UPDATE</b>\n\n{text}", parse_mode='HTML')
            sent += 1
            time.sleep(0.2)
        except:
            pass
    bot.reply_to(message, f"✅ Broadcast done. Sent: {sent}")

# -------------------- START --------------------
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id)
    welcome = (
        f"✨ <b>WELCOME {message.from_user.first_name.upper()}!</b>\n\n"
        "<b>Send any link (YouTube, TikTok, Insta, etc.) and I'll download it!</b>\n\n"
        f"💎 <b>Dev:</b> <tg-spoiler>{DEV_CREDIT}</tg-spoiler>"
    )
    bot.reply_to(message, welcome, parse_mode='HTML')

# -------------------- HANDLE LINKS --------------------
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_links(message):
    add_user(message.from_user.id)
    try:
        bot.set_message_reaction(message.chat.id, message.message_id,
                                 [telebot.types.ReactionTypeEmoji('⚡')])
    except:
        pass
    threading.Thread(target=download_media, args=(message.text.strip(), message)).start()

# -------------------- MAIN --------------------
if __name__ == "__main__":
    init_db()
    os.makedirs('downloads', exist_ok=True)

    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()

    while True:
        try:
            print("🤖 Bot polling started...")
            bot.infinity_polling(timeout=90, skip_pending=True)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)
