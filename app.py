import os
import telebot
import yt_dlp
import threading
import time
import requests
import sqlite3
from flask import Flask

# --- FLASK FOR RENDER DEPLOYMENT ---
app = Flask(__name__)

@app.route('/')
def home():
    return "AAVYA V4 DATABASE ACTIVE 🚀", 200

# --- CONFIG ---
API_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = 12345678  # <--- APNI ID YAHAN DALO
DEV_CREDIT = "@AAVYAxBOTS"

bot = telebot.TeleBot(API_TOKEN, threaded=True)

# --- DATABASE SETUP ---
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

# --- DOWNLOADER LOGIC ---
def download_media(url, message):
    msg = bot.reply_to(message, "⏳ <b><blockquote>Downloading... Please wait!</blockquote></b>", parse_mode='HTML')
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            with open(filename, 'rb') as f:
                # Caption mein Spoiler + Quote
                caption_text = (
                    "✅ <b>Downloaded Successfully!</b>\n\n"
                    f"<b><blockquote>💎 Dev: <tg-spoiler>{DEV_CREDIT}</tg-spoiler></blockquote></b>"
                )
                bot.send_video(
                    message.chat.id, 
                    f, 
                    caption=caption_text, 
                    parse_mode='HTML',
                    reply_to_message_id=message.message_id
                )
            
            if os.path.exists(filename):
                os.remove(filename)
            bot.delete_message(message.chat.id, msg.message_id)
            
    except Exception as e:
        error_text = f"❌ <b>Error:</b> Link not supported!\n<code>{str(e)[:100]}</code>"
        bot.edit_message_text(error_text, message.chat.id, msg.message_id, parse_mode='HTML')

# --- ADMIN: BROADCAST ---
@bot.message_handler(commands=['broadcast'], func=lambda m: m.from_user.id == OWNER_ID)
def broadcast_command(message):
    msg_text = message.text.replace('/broadcast', '').strip()
    if not msg_text:
        bot.reply_to(message, "<b><blockquote>Bhai, message toh likho!</blockquote></b>", parse_mode='HTML')
        return

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()

    bot.reply_to(message, "🚀 <b><blockquote>Broadcast shuru ho raha hai...</blockquote></b>", parse_mode='HTML')

    for user in users:
        try:
            bot.send_message(user[0], f"📢 <b>UPDATE</b>\n\n<b><blockquote>{msg_text}</blockquote></b>", parse_mode='HTML')
            time.sleep(0.2)
        except:
            continue

    bot.send_message(message.chat.id, "✅ <b><blockquote>BROADCAST FINISHED</blockquote></b>", parse_mode='HTML')

# --- COMMAND: START ---
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id)
    welcome = (
        f"✨ <b>WELCOME {message.from_user.first_name.upper()}!</b> ✨\n\n"
        "<b><blockquote>Main ek Advanced Downloader hoon. Link bhejein aur magic dekhein!</blockquote></b>\n\n"
        f"<b><blockquote>💎 Dev: <tg-spoiler>{DEV_CREDIT}</tg-spoiler></blockquote></b>"
    )
    bot.reply_to(message, welcome, parse_mode='HTML')

# --- HANDLER: ALL LINKS ---
@bot.message_handler(func=lambda m: m.text and ("http" in m.text))
def handle_all_links(message):
    add_user(message.from_user.id)
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [telebot.types.ReactionTypeEmoji('⚡')])
    except:
        pass
    threading.Thread(target=download_media, args=(message.text.strip(), message)).start()

# --- MAIN RUNNER ---
if __name__ == "__main__":
    init_db()
    if not os.path.exists('downloads'): os.makedirs('downloads')
    
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    while True:
        try:
            bot.infinity_polling(timeout=90, skip_pending=True)
        except Exception:
            time.sleep(5)
