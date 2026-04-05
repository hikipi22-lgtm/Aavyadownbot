import os, telebot, yt_dlp, threading, time, requests, sqlite3
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "AAVYA V4 DATABASE ACTIVE 🚀", 200

# --- CONFIG ---
API_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = 12345678  # <--- APNI ID DALO
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
    msg = bot.reply_to(message, "⏳ **Downloading... Please wait!**", parse_mode='Markdown')
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            with open(filename, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ **Downloaded!**\n\n💎 **Dev:** {DEV_CREDIT}", parse_mode='Markdown')
            
            os.remove(filename)
            bot.delete_message(message.chat.id, msg.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ **Error:** Link not supported!\n`{str(e)[:50]}`", message.chat.id, msg.message_id, parse_mode='Markdown')

# --- ADMIN LOGIC ---
@bot.message_handler(commands=['broadcast'], func=lambda m: m.from_user.id == OWNER_ID)
def broadcast_command(message):
    msg_text = message.text.replace('/broadcast', '').strip()
    if not msg_text:
        bot.reply_to(message, "<b><blockquote>Bhai, message toh likho! Example: /broadcast Hello Users</blockquote></b>", parse_mode='HTML')
        return

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()

    success, fail = 0, 0
    bot.reply_to(message, f"🚀 <b><blockquote>Broadcast shuru ho raha hai {len(users)} users ko...</blockquote></b>", parse_mode='HTML')

    for user in users:
        try:
            bot.send_message(user[0], f"📢 <b>IMPORTANT UPDATE</b>\n\n<b><blockquote>{msg_text}</blockquote></b>", parse_mode='HTML')
            success += 1
            time.sleep(0.1)
        except:
            fail += 1

    bot.send_message(message.chat.id, f"✅ <b>BROADCAST FINISHED</b>\n\n<b><blockquote>Success: {success}\nFailed: {fail}</blockquote></b>", parse_mode='HTML')

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id)
    welcome = (
        f"✨ <b>WELCOME {message.from_user.first_name.upper()}!</b> ✨\n\n"
        "<b><blockquote>Main ek Advanced Downloader hoon. Link bhejein aur magic dekhein!</blockquote></b>\n\n"
        f"💎 <b>Dev:</b> <tg-spoiler>{DEV_CREDIT}</tg-spoiler>"
    )
    bot.reply_to(message, welcome, parse_mode='HTML')

# --- NEW: HANDLING LINKS & REPLIES IN GROUPS ---
@bot.message_handler(func=lambda m: m.text and ("http" in m.text))
def handle_all_links(message):
    add_user(message.from_user.id)
    
    # Reaction Logic
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [telebot.types.ReactionTypeEmoji('🔥')])
    except:
        pass
        
    threading.Thread(target=download_media, args=(message.text.strip(), message)).start()

if __name__ == "__main__":
    init_db()
    if not os.path.exists('downloads'): os.makedirs('downloads')
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.infinity_polling(timeout=90, skip_pending=True)
