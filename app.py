import os
import re
import tempfile
import shutil
import telebot
import yt_dlp
import threading
import time
import sqlite3
from flask import Flask

# -------------------- FLASK --------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "AAVYA V4 DATABASE ACTIVE 🚀", 200

# -------------------- CONFIG --------------------
API_TOKEN = os.getenv('BOT_TOKEN')
if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN not set!")

OWNER_ID = int(os.getenv('OWNER_ID', '12345678'))
DEV_CREDIT = "@AAVYAxBOTS"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 🍪 Cookies from env string
COOKIES_STRING = os.getenv('INSTAGRAM_COOKIES', '')

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

# -------------------- SAFE FILENAME --------------------
def safe_filename(text):
    """Remove special characters and limit length"""
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > 100:
        text = text[:100]
    return text or "media"

# -------------------- DOWNLOADER --------------------
def download_media(url, message):
    msg = bot.reply_to(message, "⏳ <b><blockquote>Downloading... Please wait!</blockquote></b>", parse_mode='HTML')

    # Create temp cookie file
    cookie_file_path = None
    if COOKIES_STRING.strip():
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(COOKIES_STRING)
            cookie_file_path = f.name

    # Use a temp directory for downloads to avoid rename issues
    download_dir = tempfile.mkdtemp(prefix="ytdl_")
    os.makedirs(download_dir, exist_ok=True)

    ydl_opts = {
        'format': 'best[ext=mp4]/best[ext=mp4]/best',
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'user_agent': USER_AGENT,
        'retries': 10,
        'fragment_retries': 10,
        'extractor_retries': 5,
        'skip_unavailable_fragments': False,
        'restrictfilenames': True,
    }

    if cookie_file_path:
        ydl_opts['cookiefile'] = cookie_file_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if 'entries' in info:
                info = info['entries'][0]

            formats = info.get('formats', [])
            has_video = any(f.get('vcodec') != 'none' for f in formats)

            if not has_video and info.get('thumbnail'):
                # Image post
                ydl_opts['format'] = 'best[ext=jpg]/best[ext=png]/best[ext=webp]/best'
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_img:
                    info = ydl_img.extract_info(url, download=True)
                    filename = ydl_img.prepare_filename(info)
            else:
                # Video post
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_vid:
                    info = ydl_vid.extract_info(url, download=True)
                    filename = ydl_vid.prepare_filename(info)
                    if 'entries' in info:
                        info = info['entries'][0]
                        filename = ydl_vid.prepare_filename(info)

            # Handle missing extension
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for ext in ['.mp4', '.mkv', '.webm', '.jpg', '.png', '.jpeg', '.webp']:
                    test = base + ext
                    if os.path.exists(test):
                        filename = test
                        break

            # Move to final safe location
            final_dir = 'downloads'
            os.makedirs(final_dir, exist_ok=True)
            final_filename = os.path.join(final_dir, f"{safe_filename(info.get('title', 'media'))}{os.path.splitext(filename)[1]}")
            shutil.move(filename, final_filename)
            filename = final_filename

            with open(filename, 'rb') as f:
                caption_text = (
                    "✅ <b>Downloaded Successfully!</b>\n\n"
                    f"<b><blockquote>💎 Dev: <tg-spoiler>{DEV_CREDIT}</tg-spoiler></blockquote></b>"
                )

                ext = os.path.splitext(filename)[1].lower()
                if ext in ['.mp4', '.mkv', '.webm', '.avi']:
                    bot.send_video(
                        message.chat.id,
                        f,
                        caption=caption_text,
                        parse_mode='HTML',
                        reply_to_message_id=message.message_id
                    )
                elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    bot.send_photo(
                        message.chat.id,
                        f,
                        caption=caption_text,
                        parse_mode='HTML',
                        reply_to_message_id=message.message_id
                    )
                else:
                    bot.send_document(
                        message.chat.id,
                        f,
                        caption=caption_text,
                        parse_mode='HTML',
                        reply_to_message_id=message.message_id
                    )

            os.remove(filename)
            bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        error_str = str(e)
        if "instagram" in url.lower() and ("login" in error_str.lower() or "429" in error_str):
            reply = (
                "❌ <b>Instagram login required or rate limited.</b>\n\n"
                "👉 Ensure <code>INSTAGRAM_COOKIES</code> env var has fresh cookies.\n"
                "⚡ YouTube, TikTok, etc. will still work."
            )
        elif "no video formats" in error_str.lower():
            reply = "❌ <b>No video found in this post.</b> It might be an image-only post. Try again with a reel link."
        else:
            reply = f"❌ <b>Error:</b> <code>{error_str[:200]}</code>"
        bot.edit_message_text(reply, message.chat.id, msg.message_id, parse_mode='HTML')
    finally:
        if cookie_file_path and os.path.exists(cookie_file_path):
            os.unlink(cookie_file_path)
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)

# -------------------- BROADCAST --------------------
@bot.message_handler(commands=['broadcast'], func=lambda m: m.from_user.id == OWNER_ID)
def broadcast_command(message):
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        bot.reply_to(message, "<b><blockquote>Bhai, message toh likho!</blockquote></b>", parse_mode='HTML')
        return

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()

    bot.reply_to(message, "🚀 <b><blockquote>Broadcast shuru ho raha hai...</blockquote></b>", parse_mode='HTML')
    sent, failed = 0, 0
    for user in users:
        try:
            bot.send_message(
                user[0],
                f"📢 <b>UPDATE</b>\n\n<b><blockquote>{text}</blockquote></b>",
                parse_mode='HTML'
            )
            sent += 1
            time.sleep(0.2)
        except:
            failed += 1

    bot.send_message(
        message.chat.id,
        f"✅ <b><blockquote>BROADCAST FINISHED</blockquote></b>\n✅ Sent: {sent}\n❌ Failed: {failed}",
        parse_mode='HTML'
    )

# -------------------- START --------------------
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id)
    welcome = (
        f"✨ <b>WELCOME {message.from_user.first_name.upper()}!</b> ✨\n\n"
        "<b><blockquote>Main ek Advanced Downloader hoon. Link bhejein aur magic dekhein!</blockquote></b>\n\n"
        f"<b><blockquote>💎 Dev: <tg-spoiler>{DEV_CREDIT}</tg-spoiler></blockquote></b>"
    )
    bot.reply_to(message, welcome, parse_mode='HTML')

# -------------------- HANDLE LINKS (WITH REACTION) --------------------
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_all_links(message):
    add_user(message.from_user.id)
    try:
        # Try to set reaction
        bot.set_message_reaction(
            message.chat.id,
            message.message_id,
            [telebot.types.ReactionTypeEmoji('⚡')]
        )
    except AttributeError:
        # Older library fallback
        pass
    except Exception:
        # Any other error - ignore
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
