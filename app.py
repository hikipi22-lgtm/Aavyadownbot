import os
import telebot
import yt_dlp
import threading
import time
import sqlite3
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "AAVYA V4 DATABASE ACTIVE 🚀", 200

API_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', '12345678'))
DEV_CREDIT = "@AAVYAxBOTS"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

bot = telebot.TeleBot(API_TOKEN, threaded=True)

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

def download_media(url, message):
    msg = bot.reply_to(message, "⏳ Downloading...", parse_mode='HTML')
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'user_agent': USER_AGENT,
        'retries': 5,
        'fragment_retries': 5,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if 'entries' in info:
                info = info['entries'][0]
                filename = ydl.prepare_filename(info)
            with open(filename, 'rb') as f:
                caption = f"✅ Downloaded!\n💎 Dev: {DEV_CREDIT}"
                ext = os.path.splitext(filename)[1].lower()
                if ext in ['.mp4', '.mkv', '.webm']:
                    bot.send_video(message.chat.id, f, caption=caption, reply_to_message_id=message.message_id)
                elif ext in ['.jpg', '.png', '.jpeg']:
                    bot.send_photo(message.chat.id, f, caption=caption, reply_to_message_id=message.message_id)
                else:
                    bot.send_document(message.chat.id, f, caption=caption, reply_to_message_id=message.message_id)
            os.remove(filename)
            bot.delete_message(message.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)[:200]}", message.chat.id, msg.message_id, parse_mode='HTML')

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
            bot.send_message(user[0], f"📢 UPDATE\n\n{text}")
            sent += 1
            time.sleep(0.2)
        except:
            pass
    bot.reply_to(message, f"✅ Broadcast done. Sent: {sent}")

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id)
    welcome = f"✨ WELCOME {message.from_user.first_name.upper()}!\n\nMain ek downloader bot hoon. Link bhejo, video lo!\n\n💎 Dev: {DEV_CREDIT}"
    bot.reply_to(message, welcome)

@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_links(message):
    add_user(message.from_user.id)
    threading.Thread(target=download_media, args=(message.text.strip(), message)).start()

if __name__ == "__main__":
    init_db()
    os.makedirs('downloads', exist_ok=True)
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    while True:
        try:
            bot.infinity_polling(timeout=90, skip_pending=True)
        except:
            time.sleep(5)
