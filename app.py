import os, telebot, yt_dlp, threading, time, sqlite3
from flask import Flask

# --- FLASK FOR DEPLOYMENT ---
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

# --- DOWNLOAD LOGIC ---
def download_video(url, message):
    msg = bot.reply_to(message, "⏳ **Processing your link...**", parse_mode='Markdown')
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            with open(filename, 'rb') as video:
                bot.send_video(message.chat.id, video, caption=f"✅ **Downloaded Successfully!**\n\n💎 **Dev:** {DEV_CREDIT}", parse_mode='Markdown')
            
            os.remove(filename) # Phone/Server memory clean karne ke liye
            bot.delete_message(message.chat.id, msg.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ **Error:** Link support nahi kar raha ya private hai.\n`{str(e)[:50]}`", message.chat.id, msg.message_id, parse_mode='Markdown')

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id)
    welcome = (
        f"✨ **WELCOME {message.from_user.first_name.upper()}!** ✨\n\n"
        "**Main sabhi social media links download kar sakta hoon.**\n"
        "Bas link bhejo aur download shuru!"
    )
    bot.reply_to(message, welcome, parse_mode='Markdown')

@bot.message_handler(commands=['broadcast'], func=lambda m: m.from_user.id == OWNER_ID)
def broadcast_command(message):
    msg_text = message.text.replace('/broadcast', '').strip()
    if not msg_text:
        bot.reply_to(message, "Bhai, message toh likho!")
        return

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()

    bot.reply_to(message, f"🚀 Broadcast shuru: {len(users)} users.")
    for user in users:
        try:
            bot.send_message(user[0], f"📢 **UPDATE**\n\n{msg_text}", parse_mode='Markdown')
            time.sleep(0.1)
        except: continue
    bot.send_message(message.chat.id, "✅ Broadcast complete!")

# --- LINK HANDLER (Groups + Private) ---
@bot.message_handler(func=lambda m: m.text and ("http://" in m.text or "https://" in m.text))
def handle_links(message):
    add_user(message.from_user.id)
    # Reaction feature (Sirf updated Telegram versions ke liye)
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [telebot.types.ReactionTypeEmoji('⚡')])
    except:
        pass
        
    url = message.text.strip()
    threading.Thread(target=download_video, args=(url, message)).start()

# --- RUN ---
if __name__ == "__main__":
    init_db()
    if not os.path.exists('downloads'): os.makedirs('downloads')
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    print("Bot is alive...")
    bot.infinity_polling(timeout=90, skip_pending=True)
