#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║       🎬  DarkX Downloader Bot  — Ultimate Edition  🎬              ║
║  ReplyKeyboard UI | Quality Picker | 500 MB | Full Admin Panel      ║
║  Modified with Environment Vars | Credits: @aavyaxbots               ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import csv
import io
import logging
import os
import re
import sqlite3
import tempfile
import traceback
from datetime import datetime
from typing import Optional

import pytz
import yt_dlp
from telegram import (
    BotCommand,
    ChatMember,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    ReactionTypeEmoji,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ═══════════════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURATION (Environment Variables)
# ═══════════════════════════════════════════════════════════════════════

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable not set!")

ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
SEED_ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip()]
if not SEED_ADMIN_IDS:
    SEED_ADMIN_IDS = [8546440950, 8517539413]  # fallback (optional)

TIMEZONE        = pytz.timezone("Asia/Kolkata")
DB_PATH         = "darkx_bot.db"

MAX_FILE_MB     = 500
LOCAL_API_URL   = os.getenv("LOCAL_API_URL", "")

QUALITY_FORMATS = {
    "audio": "bestaudio[ext=m4a]/bestaudio/best",
    "360":   "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]/best",
    "480":   "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best",
    "720":   "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
    "1080":  "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]/best",
    "best":  "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
}

# 🚀 UPDATED: Only 2 Force-Join Channels
DEFAULT_CHANNELS = [
    {"id": "@aavyaxbots", "name": "AAVYAxBOTS Channel"},
    {"id": "@ffofcchat",  "name": "FF OFC Chat Group"},
]

CREDIT_LINE = "> 💎 *Dev:* ||@aavyaxbots||"

# ═══════════════════════════════════════════════════════════════════════
#  📋  LOGGING
# ═══════════════════════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("DarkXBot")

# ═══════════════════════════════════════════════════════════════════════
#  🗄️  DATABASE
# ═══════════════════════════════════════════════════════════════════════

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT    NOT NULL DEFAULT 'User',
            last_name   TEXT,
            join_date   TEXT    NOT NULL DEFAULT (datetime('now')),
            last_active TEXT    NOT NULL DEFAULT (datetime('now')),
            is_banned   INTEGER NOT NULL DEFAULT 0,
            downloads   INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS admins (
            user_id  INTEGER PRIMARY KEY,
            added_by INTEGER,
            added_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS channels (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id   TEXT    NOT NULL UNIQUE,
            channel_name TEXT,
            added_by     INTEGER,
            added_date   TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS downloads (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER NOT NULL,
            url       TEXT,
            platform  TEXT,
            quality   TEXT    DEFAULT 'best',
            status    TEXT    NOT NULL DEFAULT 'success',
            file_size REAL    DEFAULT 0,
            timestamp TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS support_messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            message_id INTEGER,
            bot_msg_id INTEGER,
            replied    INTEGER NOT NULL DEFAULT 0,
            timestamp  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS broadcast_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id  INTEGER,
            bc_type   TEXT,
            total     INTEGER DEFAULT 0,
            sent      INTEGER DEFAULT 0,
            failed    INTEGER DEFAULT 0,
            timestamp TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        """)

    with get_db() as conn:
        for aid in SEED_ADMIN_IDS:
            conn.execute(
                "INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?,?)",
                (aid, aid),
            )
        for ch in DEFAULT_CHANNELS:
            conn.execute(
                "INSERT OR IGNORE INTO channels (channel_id, channel_name, added_by)"
                " VALUES (?,?,?)",
                (ch["id"], ch["name"], SEED_ADMIN_IDS[0]),
            )
        conn.execute(
            "INSERT OR IGNORE INTO settings VALUES ('default_msg',?)",
            ("🎬 *Welcome!* You are all set!\n"
             "Send me any video link and I'll download it instantly! 🚀\n\n"
             f"{CREDIT_LINE}",),
        )
    logger.info("Database ready ✅")

# ──────────────────────────────────────────────────────────────────────
#  Helper functions (register, ban, admin, stats, etc.)
# ──────────────────────────────────────────────────────────────────────

def register_user(user) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)"
            " VALUES (?,?,?,?)",
            (user.id, user.username, user.first_name, user.last_name),
        )
        conn.execute(
            "UPDATE users SET username=?, first_name=?, last_name=?,"
            " last_active=datetime('now') WHERE user_id=?",
            (user.username, user.first_name, user.last_name, user.id),
        )

def is_banned(user_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT is_banned FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        return bool(row and row["is_banned"])

def ban_user(user_id: int) -> None:
    with get_db() as conn:
        conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))

def unban_user(user_id: int) -> None:
    with get_db() as conn:
        conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))

def get_all_users():
    with get_db() as conn:
        return conn.execute("SELECT * FROM users ORDER BY join_date DESC").fetchall()

def get_broadcast_user_ids():
    with get_db() as conn:
        return [
            r["user_id"]
            for r in conn.execute(
                "SELECT user_id FROM users WHERE is_banned=0"
            ).fetchall()
        ]

def is_admin(user_id: int) -> bool:
    with get_db() as conn:
        return conn.execute(
            "SELECT user_id FROM admins WHERE user_id=?", (user_id,)
        ).fetchone() is not None

def get_all_admins():
    with get_db() as conn:
        return [r["user_id"] for r in conn.execute("SELECT user_id FROM admins").fetchall()]

def add_admin_db(user_id: int, added_by: int) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?,?)",
            (user_id, added_by),
        )

def remove_admin_db(user_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM admins WHERE user_id=?", (user_id,))

def get_all_channels():
    with get_db() as conn:
        return conn.execute("SELECT * FROM channels").fetchall()

def add_channel(channel_id: str, channel_name: str, added_by: int) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO channels (channel_id, channel_name, added_by)"
            " VALUES (?,?,?)",
            (channel_id, channel_name, added_by),
        )

def remove_channel(channel_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM channels WHERE channel_id=?", (channel_id,))

def log_download(user_id: int, url: str, platform: str, quality: str,
                 status: str = "success", file_size: float = 0) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO downloads (user_id, url, platform, quality, status, file_size)"
            " VALUES (?,?,?,?,?,?)",
            (user_id, url, platform, quality, status, file_size),
        )
        if status == "success":
            conn.execute(
                "UPDATE users SET downloads=downloads+1 WHERE user_id=?", (user_id,)
            )

def get_stats() -> dict:
    with get_db() as conn:
        def count(q):
            return conn.execute(q).fetchone()[0]
        return {
            "total_users":     count("SELECT COUNT(*) FROM users"),
            "banned_users":    count("SELECT COUNT(*) FROM users WHERE is_banned=1"),
            "active_today":    count("SELECT COUNT(*) FROM users WHERE last_active>=date('now')"),
            "active_week":     count("SELECT COUNT(*) FROM users WHERE last_active>=date('now','-7 days')"),
            "total_downloads": count("SELECT COUNT(*) FROM downloads"),
            "today_downloads": count("SELECT COUNT(*) FROM downloads WHERE timestamp>=date('now')"),
            "success_dl":      count("SELECT COUNT(*) FROM downloads WHERE status='success'"),
            "failed_dl":       count("SELECT COUNT(*) FROM downloads WHERE status!='success'"),
            "channels_count":  count("SELECT COUNT(*) FROM channels"),
            "admins_count":    count("SELECT COUNT(*) FROM admins"),
            "broadcasts":      count("SELECT COUNT(*) FROM broadcast_log"),
        }

def get_setting(key: str) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

def set_setting(key: str, value: str) -> None:
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, value))

def now_ist() -> str:
    return datetime.now(TIMEZONE).strftime("%d %b %Y • %I:%M %p IST")

def detect_platform(url: str) -> str:
    patterns = {
        "YouTube":     r"(youtube\.com|youtu\.be)",
        "Instagram":   r"instagram\.com",
        "TikTok":      r"tiktok\.com",
        "Twitter / X": r"(twitter\.com|x\.com)",
        "Facebook":    r"facebook\.com",
        "Reddit":      r"reddit\.com",
        "Pinterest":   r"pinterest\.com",
        "Dailymotion": r"dailymotion\.com",
        "Vimeo":       r"vimeo\.com",
    }
    for platform, pattern in patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "Unknown Platform"

def extract_url(text: str) -> Optional[str]:
    m = re.search(r"https?://[^\s]+", text)
    return m.group() if m else None

def fmt_duration(seconds) -> str:
    if not seconds:
        return "N/A"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s   = divmod(rem, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

def fmt_size(bytes_: int) -> str:
    mb = bytes_ / (1024 * 1024)
    return f"{mb:.1f} MB"

def channel_link(ch) -> str:
    cid = ch["channel_id"]
    return f"https://t.me/{cid[1:]}" if cid.startswith("@") else f"https://t.me/{cid}"

def parse_inline_buttons(text: str):
    rows = []
    row  = []
    for line in text.strip().splitlines():
        line = line.strip()
        if "|" in line:
            parts = line.split("|", 1)
            name  = parts[0].strip()
            url   = parts[1].strip()
            if name and url.startswith("http"):
                row.append(InlineKeyboardButton(name, url=url))
                if len(row) == 2:
                    rows.append(row)
                    row = []
    if row:
        rows.append(row)
    return rows

# ═══════════════════════════════════════════════════════════════════════
#  🔒  FORCE-JOIN
# ═══════════════════════════════════════════════════════════════════════

async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> list:
    user_id  = update.effective_user.id
    channels = get_all_channels()
    missing  = []
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch["channel_id"], user_id)
            if member.status in (ChatMember.LEFT, ChatMember.BANNED):
                missing.append(ch)
        except Exception:
            missing.append(ch)
    return missing

def build_join_keyboard(missing: list) -> InlineKeyboardMarkup:
    rows = []
    row  = []
    for ch in missing:
        row.append(InlineKeyboardButton(f"📢 {ch['channel_name']}", url=channel_link(ch)))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("✅ I've Joined — Verify Now!", callback_data="verify_join")])
    return InlineKeyboardMarkup(rows)

# ═══════════════════════════════════════════════════════════════════════
#  ⌨️  KEYBOARDS
# ═══════════════════════════════════════════════════════════════════════

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📥 How to Download"), KeyboardButton("📊 My Stats")],
            [KeyboardButton("🌐 Supported Sites"),  KeyboardButton("💬 Support")],
            [KeyboardButton("👥 Our Channels")],
        ],
        resize_keyboard=True,
    )

def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📢 Broadcast"),       KeyboardButton("📊 Statistics")],
            [KeyboardButton("🚫 Ban User"),         KeyboardButton("✅ Unban User")],
            [KeyboardButton("📡 Add Channel"),      KeyboardButton("❌ Remove Channel")],
            [KeyboardButton("👑 Add Admin"),        KeyboardButton("➖ Remove Admin")],
            [KeyboardButton("💌 Default Message"),  KeyboardButton("📦 Extract DB")],
            [KeyboardButton("📥 Add Data"),         KeyboardButton("👥 View Users")],
            [KeyboardButton("🔙 Back to Menu")],
        ],
        resize_keyboard=True,
    )

def broadcast_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📨 Normal Broadcast")],
            [KeyboardButton("🔘 Button Broadcast")],
            [KeyboardButton("💎 Premium Broadcast")],
            [KeyboardButton("🔙 Back to Admin")],
        ],
        resize_keyboard=True,
    )

def quality_picker_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 Audio Only", callback_data="q_audio"),
            InlineKeyboardButton("📱 360p",       callback_data="q_360"),
        ],
        [
            InlineKeyboardButton("📺 480p",       callback_data="q_480"),
            InlineKeyboardButton("🖥 720p HD",    callback_data="q_720"),
        ],
        [
            InlineKeyboardButton("🖥 1080p FHD",  callback_data="q_1080"),
            InlineKeyboardButton("⚡ Best",        callback_data="q_best"),
        ],
        [
            InlineKeyboardButton("❌ Cancel",      callback_data="q_cancel"),
        ],
    ])

# ═══════════════════════════════════════════════════════════════════════
#  🏠  /start
# ═══════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register_user(user)

    if is_banned(user.id):
        await update.message.reply_text("🚫 You have been banned from this bot.")
        return

    missing = await check_force_join(update, context)
    if missing:
        await update.message.reply_text(
            f"👋 *Welcome to DarkX Downloader!*\n\n"
            f"🔒 You must join our official channels to use this bot:\n\n"
            + "\n".join(f"  • {ch['channel_name']}" for ch in missing)
            + f"\n\n{CREDIT_LINE}\n\n✅ After joining, tap *Verify* below.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=build_join_keyboard(missing),
        )
        return

    await _send_welcome(update, context, user)

async def _send_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    default_msg = get_setting("default_msg") or "Send me any video link to download! 🎬"
    context.user_data["in_admin_panel"] = False
    context.user_data["admin_state"]    = None
    await update.message.reply_text(
        f"🎬 *Welcome, {user.first_name}!*\n\n"
        f"{default_msg}\n\n"
        f"╔════════════════════════╗\n"
        f"║   🚀 *DarkX Downloader*  ║\n"
        f"╚════════════════════════╝\n\n"
        f"🌍 *Supported:* YouTube • Instagram • TikTok • Twitter/X • Facebook • Reddit & 1000+ more!\n\n"
        f"{CREDIT_LINE}\n\n"
        f"🕐 `{now_ist()}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(),
    )

# ═══════════════════════════════════════════════════════════════════════
#  🛡️  /admin
# ═══════════════════════════════════════════════════════════════════════

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ You are not an admin.")
        return
    context.user_data["in_admin_panel"] = True
    context.user_data["admin_state"]    = None
    await update.message.reply_text(
        "🛡 *Admin Panel*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 *Welcome, {user.first_name}!*\n"
        f"{CREDIT_LINE}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Choose an option below:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_menu_kb(),
    )

# ═══════════════════════════════════════════════════════════════════════
#  ❓  /help
# ═══════════════════════════════════════════════════════════════════════

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    register_user(user)
    if is_admin(user.id):
        text = (
            "🛠 *Admin Commands*\n\n"
            "🛡 `/admin` — Open admin panel\n"
            "📊 `/statistics` — Bot statistics\n"
            "📢 `/darkchannel @ch [Name]` — Add force-join channel\n"
            "❌ `/removechannel` — Remove a channel\n"
            "📣 `/broadcast` — Broadcast message\n"
            "👥 `/users` — View all users\n"
            "🚫 `/ban <user_id>` — Ban a user\n"
            "✅ `/unban <user_id>` — Unban a user\n\n"
            "────────────────────\n"
            "👤 *User Commands*\n\n"
            "/start — Start the bot\n"
            "/help  — This message\n\n"
            f"{CREDIT_LINE}"
        )
    else:
        text = (
            "❓ *Help Guide*\n\n"
            "/start — Start the bot\n"
            "/help  — This message\n\n"
            "📌 *How to download:*\n"
            "1️⃣ Copy any video URL\n"
            "2️⃣ Paste it here\n"
            "3️⃣ Pick your quality\n"
            "4️⃣ Get your video! 🎉\n\n"
            "🌐 *Supported:*\n"
            "YouTube • Instagram • TikTok • Twitter/X\n"
            "Facebook • Reddit • Pinterest & 1000+ more!\n\n"
            f"{CREDIT_LINE}"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ═══════════════════════════════════════════════════════════════════════
#  📊  /statistics
# ═══════════════════════════════════════════════════════════════════════

async def cmd_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admins only.")
        return
    await _send_statistics(update.message)

async def _send_statistics(target) -> None:
    s = get_stats()
    dl_rate = f"{s['success_dl'] / max(1, s['total_downloads']) * 100:.1f}%"
    text = (
        "📊 *Bot Statistics*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *Total Users:*      `{s['total_users']}`\n"
        f"🚫 *Banned Users:*     `{s['banned_users']}`\n"
        f"🟢 *Active Today:*     `{s['active_today']}`\n"
        f"📅 *Active This Week:* `{s['active_week']}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📥 *Total Downloads:*  `{s['total_downloads']}`\n"
        f"🆕 *Today Downloads:*  `{s['today_downloads']}`\n"
        f"✅ *Successful DLs:*   `{s['success_dl']}`\n"
        f"❌ *Failed DLs:*       `{s['failed_dl']}`\n"
        f"📈 *Success Rate:*     `{dl_rate}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 *Force-Join Channels:* `{s['channels_count']}`\n"
        f"👑 *Admins:*              `{s['admins_count']}`\n"
        f"📣 *Broadcasts Sent:*     `{s['broadcasts']}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{CREDIT_LINE}\n"
        f"🕐 `{now_ist()}`"
    )
    await target.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ═══════════════════════════════════════════════════════════════════════
#  📢  /darkchannel  /removechannel
# ═══════════════════════════════════════════════════════════════════════

async def cmd_darkchannel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: `/darkchannel @username Channel Name`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    channel_id = context.args[0]
    if not channel_id.startswith("@"):
        channel_id = "@" + channel_id
    channel_name = " ".join(context.args[1:]) if len(context.args) > 1 else channel_id[1:]
    try:
        chat = await context.bot.get_chat(channel_id)
        channel_name = chat.title or channel_name
    except Exception:
        pass
    add_channel(channel_id, channel_name, update.effective_user.id)
    await update.message.reply_text(
        f"✅ *Channel Added!*\n📢 {channel_name} (`{channel_id}`)\n{CREDIT_LINE}",
        parse_mode=ParseMode.MARKDOWN,
    )

async def cmd_removechannel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    channels = get_all_channels()
    if not channels:
        await update.message.reply_text("📭 No channels configured.")
        return
    text    = "📋 *Force-Join Channels* — tap to remove:\n\n"
    buttons = []
    for ch in channels:
        text += f"• `{ch['channel_id']}` — {ch['channel_name']}\n"
        safe  = ch["channel_id"].replace("@", "AT_")
        buttons.append([InlineKeyboardButton(
            f"❌ Remove {ch['channel_name']}", callback_data=f"rmch_{safe}"
        )])
    text += f"\n{CREDIT_LINE}"
    await update.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# ═══════════════════════════════════════════════════════════════════════
#  🚫  /ban  /unban
# ═══════════════════════════════════════════════════════════════════════

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/ban <user_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        uid = int(context.args[0])
        ban_user(uid)
        await update.message.reply_text(f"✅ User `{uid}` banned.\n{CREDIT_LINE}", parse_mode=ParseMode.MARKDOWN)
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")

async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/unban <user_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        uid = int(context.args[0])
        unban_user(uid)
        await update.message.reply_text(f"✅ User `{uid}` unbanned.\n{CREDIT_LINE}", parse_mode=ParseMode.MARKDOWN)
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")

# ═══════════════════════════════════════════════════════════════════════
#  📣  /broadcast
# ═══════════════════════════════════════════════════════════════════════

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    msg = update.message
    if msg.reply_to_message:
        bc_msg = msg.reply_to_message
        context.bot_data["bc_msg"]          = bc_msg
        context.bot_data["bc_text_override"] = None
        context.bot_data["bc_buttons"]       = None
        preview = bc_msg.text or bc_msg.caption or "[Media]"
        preview = preview[:200] + "…" if len(preview) > 200 else preview
        await msg.reply_text(
            f"📣 *Broadcast Preview*\n\n_{preview}_\n\nAdd inline buttons?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔘 Add Buttons",     callback_data="bc_add_btn")],
                [InlineKeyboardButton("⏭ Send Now",         callback_data="bc_send")],
            ]),
        )
    elif context.args:
        text = " ".join(context.args)
        context.bot_data["bc_msg"]           = msg
        context.bot_data["bc_text_override"] = text
        context.bot_data["bc_buttons"]       = None
        await msg.reply_text(
            f"📣 *Broadcast:* _{text[:200]}_\n\nSend now?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭ Send Now", callback_data="bc_send")],
            ]),
        )
    else:
        await msg.reply_text(
            "📣 *Usage:*\n"
            "• Reply to a message with `/broadcast`\n"
            "• Or: `/broadcast Your message text`\n\n"
            "Or open the admin panel with /admin for more options.\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )

# ═══════════════════════════════════════════════════════════════════════
#  👥  /users
# ═══════════════════════════════════════════════════════════════════════

async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    msg = await _build_users_msg(0)
    await update.message.reply_text(
        msg["text"], parse_mode=ParseMode.MARKDOWN, reply_markup=msg["kb"]
    )

async def _build_users_msg(page: int) -> dict:
    users    = get_all_users()
    per_page = 5
    total    = len(users)
    pages    = max(1, -(-total // per_page))
    start    = page * per_page
    subset   = users[start:start + per_page]

    text = f"👥 *Users* | Page {page + 1}/{pages} | Total: `{total}`\n\n"
    btns = []
    for u in subset:
        icon  = "🚫" if u["is_banned"] else "✅"
        uname = f"@{u['username']}" if u["username"] else "—"
        text += (
            f"{icon} *{u['first_name']}* ({uname})\n"
            f"  🆔 `{u['user_id']}` | 📥 {u['downloads']} DLs\n\n"
        )
        label = ("✅ Unban " if u["is_banned"] else "🚫 Ban ") + u["first_name"]
        cb    = ("unban_" if u["is_banned"] else "ban_") + str(u["user_id"])
        btns.append([InlineKeyboardButton(label, callback_data=cb)])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"upage_{page - 1}"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"upage_{page + 1}"))
    if nav:
        btns.append(nav)

    text += f"\n{CREDIT_LINE}"
    return {"text": text, "kb": InlineKeyboardMarkup(btns) if btns else None}

# ═══════════════════════════════════════════════════════════════════════
#  📦  DB EXTRACT HELPER
# ═══════════════════════════════════════════════════════════════════════

async def send_db_extract(target) -> None:
    users = get_all_users()
    buf   = io.StringIO()
    w     = csv.writer(buf)
    w.writerow(["user_id", "username", "first_name", "last_name",
                "join_date", "last_active", "is_banned", "downloads"])
    for u in users:
        w.writerow([u["user_id"], u["username"], u["first_name"], u["last_name"],
                    u["join_date"], u["last_active"], u["is_banned"], u["downloads"]])
    buf.seek(0)
    await target.reply_document(
        document=buf.getvalue().encode(),
        filename=f"users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        caption=f"📊 *Users CSV Export*\n👥 `{len(users)}` users total\n{CREDIT_LINE}",
        parse_mode=ParseMode.MARKDOWN,
    )
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "rb") as f:
            await target.reply_document(
                document=f,
                filename="darkx_bot.db",
                caption=f"🗄 *Full Database Backup* — SQLite .db file\n{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
            )

# ═══════════════════════════════════════════════════════════════════════
#  📣  BROADCAST ENGINE
# ═══════════════════════════════════════════════════════════════════════

async def _execute_broadcast(
    context: ContextTypes.DEFAULT_TYPE,
    admin_id: int,
    bc_type: str,
    bc_msg=None,
    buttons=None,
    text_override: Optional[str] = None,
    is_forward: bool = False,
) -> None:
    user_ids  = get_broadcast_user_ids()
    total     = len(user_ids)
    sent      = 0
    failed    = 0
    reply_mkup = InlineKeyboardMarkup(buttons) if buttons else None

    status_msg = await context.bot.send_message(
        admin_id,
        f"📣 Broadcasting to *{total}* users...\nPlease wait ⏳\n{CREDIT_LINE}",
        parse_mode=ParseMode.MARKDOWN,
    )

    for idx, uid in enumerate(user_ids, 1):
        try:
            if is_forward and bc_msg:
                await context.bot.forward_message(
                    chat_id=uid,
                    from_chat_id=bc_msg.chat.id,
                    message_id=bc_msg.message_id,
                )
            elif text_override:
                await context.bot.send_message(
                    uid, text_override,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_mkup,
                )
            elif bc_msg and bc_msg.text:
                await context.bot.send_message(
                    uid, bc_msg.text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_mkup,
                )
            elif bc_msg and bc_msg.photo:
                await context.bot.send_photo(
                    uid, bc_msg.photo[-1].file_id,
                    caption=bc_msg.caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_mkup,
                )
            elif bc_msg and bc_msg.video:
                await context.bot.send_video(
                    uid, bc_msg.video.file_id,
                    caption=bc_msg.caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_mkup,
                )
            elif bc_msg and bc_msg.document:
                await context.bot.send_document(
                    uid, bc_msg.document.file_id,
                    caption=bc_msg.caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_mkup,
                )
            elif bc_msg and bc_msg.animation:
                await context.bot.send_animation(
                    uid, bc_msg.animation.file_id,
                    caption=bc_msg.caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_mkup,
                )
            elif bc_msg and bc_msg.sticker:
                await context.bot.send_sticker(uid, bc_msg.sticker.file_id)
            elif bc_msg and bc_msg.voice:
                await context.bot.send_voice(
                    uid, bc_msg.voice.file_id,
                    caption=bc_msg.caption,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif bc_msg:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=bc_msg.chat.id,
                    message_id=bc_msg.message_id,
                    reply_markup=reply_mkup,
                )
            sent += 1
        except Exception as e:
            logger.warning(f"Broadcast → {uid}: {e}")
            failed += 1

        if idx % 50 == 0:
            try:
                pct = int(idx / total * 100)
                await status_msg.edit_text(
                    f"📣 Broadcasting... `{pct}%`\n"
                    f"✅ `{sent}` | ❌ `{failed}` | {idx}/{total}\n"
                    f"{CREDIT_LINE}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass

        if idx % 25 == 0:
            await asyncio.sleep(1)

    with get_db() as conn:
        conn.execute(
            "INSERT INTO broadcast_log (admin_id, bc_type, total, sent, failed)"
            " VALUES (?,?,?,?,?)",
            (admin_id, bc_type, total, sent, failed),
        )

    rate = sent / max(1, sent + failed) * 100
    await status_msg.edit_text(
        f"✅ *Broadcast Complete!*\n\n"
        f"📤 Sent:    `{sent}`\n"
        f"❌ Failed:  `{failed}`\n"
        f"📊 Success: `{rate:.1f}%`\n"
        f"{CREDIT_LINE}\n"
        f"🕐 `{now_ist()}`",
        parse_mode=ParseMode.MARKDOWN,
    )

# ═══════════════════════════════════════════════════════════════════════
#  🎬  QUALITY PICKER → ask user before downloading
# ═══════════════════════════════════════════════════════════════════════

async def show_quality_picker(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               url: str) -> None:
    platform  = detect_platform(url)
    short_url = url[:55] + "…" if len(url) > 55 else url
    context.user_data["pending_url"] = url

    # 🌚 reaction on link
    try:
        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            reaction=[ReactionTypeEmoji("🌚")],
        )
    except Exception:
        pass

    await update.message.reply_text(
        f"🎬 *Select Download Quality*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 *Platform:* `{platform}`\n"
        f"🔗 *URL:* `{short_url}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 Choose your preferred quality:\n\n"
        f"{CREDIT_LINE}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=quality_picker_kb(),
    )

# ═══════════════════════════════════════════════════════════════════════
#  📥  DOWNLOAD ENGINE
# ═══════════════════════════════════════════════════════════════════════

async def _handle_download(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    url: str,
    quality: str,
    proc_msg=None,
) -> None:
    user     = update.effective_user
    chat_id  = update.effective_chat.id
    platform = detect_platform(url)
    is_audio = quality == "audio"

    short_url = url[:55] + "…" if len(url) > 55 else url

    if proc_msg is None:
        proc_msg = await context.bot.send_message(
            chat_id,
            f"⏳ *Processing your request…*\n\n"
            f"🌐 *Platform:* `{platform}`\n"
            f"🎯 *Quality:* `{quality}`\n"
            f"🔗 *URL:* `{short_url}`\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "format":                       QUALITY_FORMATS.get(quality, QUALITY_FORMATS["best"]),
                "outtmpl":                      os.path.join(tmpdir, "%(title).80s.%(ext)s"),
                "quiet":                        True,
                "no_warnings":                  True,
                "noplaylist":                   True,
                "socket_timeout":               60,
                "retries":                      5,
                "fragment_retries":             5,
                "concurrent_fragment_downloads": 8,
                "http_chunk_size":              10485760,
                "noprogress":                   True,
            }

            if is_audio:
                ydl_opts["merge_output_format"] = "mp3"
                ydl_opts["postprocessors"] = [{
                    "key":              "FFmpegExtractAudio",
                    "preferredcodec":   "mp3",
                    "preferredquality": "192",
                }]
            else:
                ydl_opts["merge_output_format"] = "mp4"
                ydl_opts["postprocessors"] = [{
                    "key":            "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }]

            await proc_msg.edit_text(
                f"⬇️ *Downloading…*\n\n"
                f"🌐 *Platform:* `{platform}`\n"
                f"🎯 *Quality:* `{quality}`\n"
                f"{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
            )

            loop = asyncio.get_event_loop()

            def do_download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=True)

            info = await loop.run_in_executor(None, do_download)

            title    = info.get("title", "Media")
            duration = info.get("duration", 0)
            uploader = info.get("uploader") or info.get("channel") or "Unknown"

            files = [f for f in os.listdir(tmpdir) if not f.endswith(".part")]
            if not files:
                raise Exception("Download produced no output file.")

            filepath = os.path.join(tmpdir, files[0])
            filesize = os.path.getsize(filepath)

            hard_limit_bytes = MAX_FILE_MB * 1024 * 1024
            if filesize > hard_limit_bytes:
                await proc_msg.edit_text(
                    f"❌ *File Too Large!*\n\n"
                    f"Size: *{fmt_size(filesize)}*\n"
                    f"Limit: *{MAX_FILE_MB} MB*\n\n"
                    f"💡 Try a lower quality option.\n"
                    f"{CREDIT_LINE}",
                    parse_mode=ParseMode.MARKDOWN,
                )
                log_download(user.id, url, platform, quality, "failed_size",
                             filesize / 1024 / 1024)
                return

            await proc_msg.edit_text(
                f"📤 *Uploading…*\n\n"
                f"📦 *Size:* `{fmt_size(filesize)}`\n"
                f"🎯 *Quality:* `{quality}`\n"
                f"{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
            )

            caption = (
                f"🎬 *{title}*\n\n"
                f"👤 *Creator:* {uploader}\n"
                f"⏱ *Duration:* {fmt_duration(duration)}\n"
                f"📦 *Size:* {fmt_size(filesize)}\n"
                f"🎯 *Quality:* `{quality}`\n"
                f"🌐 *Platform:* {platform}\n"
                f"{CREDIT_LINE}\n"
                f"🕐 `{now_ist()}`"
            )

            with open(filepath, "rb") as f:
                if is_audio:
                    sent_msg = await context.bot.send_audio(
                        chat_id,
                        f,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        title=title,
                        performer=uploader,
                        read_timeout=300,
                        write_timeout=300,
                        connect_timeout=60,
                    )
                else:
                    sent_msg = await context.bot.send_video(
                        chat_id,
                        f,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        supports_streaming=True,
                        read_timeout=300,
                        write_timeout=300,
                        connect_timeout=60,
                    )

            # 💯 reaction on original message
            if update.message:
                try:
                    await context.bot.set_message_reaction(
                        chat_id=chat_id,
                        message_id=update.message.message_id,
                        reaction=[ReactionTypeEmoji("💯")],
                    )
                except Exception:
                    pass

            try:
                await proc_msg.delete()
            except Exception:
                pass

            log_download(user.id, url, platform, quality, "success",
                         filesize / 1024 / 1024)

            uname   = f"@{user.username}" if user.username else "_No username_"
            fwd_cap = (
                f"📥 *New Download*\n"
                f"{'─' * 28}\n"
                f"👤 *User:* [{user.first_name}](tg://user?id={user.id})\n"
                f"🆔 *ID:* `{user.id}`\n"
                f"📛 *Username:* {uname}\n"
                f"{'─' * 28}\n"
                f"🌐 *Platform:* {platform}\n"
                f"🎯 *Quality:* `{quality}`\n"
                f"🎬 *Title:* {title}\n"
                f"📦 *Size:* {fmt_size(filesize)}\n"
                f"🔗 *URL:* {url}\n"
                f"{CREDIT_LINE}\n"
                f"🕐 `{now_ist()}`"
            )
            for admin_id in get_all_admins():
                try:
                    await context.bot.forward_message(
                        chat_id=admin_id,
                        from_chat_id=chat_id,
                        message_id=sent_msg.message_id,
                    )
                    await context.bot.send_message(
                        admin_id, fwd_cap, parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as fe:
                    logger.error(f"Admin fwd error ({admin_id}): {fe}")

    except yt_dlp.utils.DownloadError as e:
        err     = str(e)
        reasons = []
        if "private"       in err.lower(): reasons.append("• The video is *private*")
        if "age"           in err.lower(): reasons.append("• *Age restriction* on this video")
        if "not available" in err.lower(): reasons.append("• Video *not available* in your region")
        if "unsupported"   in err.lower(): reasons.append("• Platform *not supported*")
        if not reasons:                    reasons.append("• Link may be *invalid or expired*")
        logger.error(f"yt-dlp error: {err}")
        log_download(user.id, url, platform, quality, "failed")
        await proc_msg.edit_text(
            f"❌ *Download Failed!*\n\nReasons:\n" + "\n".join(reasons) +
            f"\n\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )

    except Exception:
        logger.error(traceback.format_exc())
        log_download(user.id, url, platform, quality, "failed")
        try:
            await proc_msg.edit_text(
                "❌ *Something went wrong!*\n\n"
                "Please try again. If the problem persists, contact support.\n"
                f"{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════════════
#  🔘  CALLBACK HANDLER
# ═══════════════════════════════════════════════════════════════════════

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user  = query.from_user
    await query.answer()
    data = query.data

    if data == "verify_join":
        missing = await check_force_join(update, context)
        if missing:
            await query.answer("❌ You haven't joined all channels!", show_alert=True)
            await query.edit_message_reply_markup(reply_markup=build_join_keyboard(missing))
        else:
            try:
                await query.message.delete()
            except Exception:
                pass
            default_msg = get_setting("default_msg") or "Send me a video link! 🎬"
            context.user_data["in_admin_panel"] = False
            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    f"✅ *Verified!*\n\n"
                    f"🎉 Welcome, *{user.first_name}*!\n\n"
                    f"{default_msg}\n\n"
                    f"╔════════════════════════╗\n"
                    f"║   🚀 *DarkX Downloader*  ║\n"
                    f"╚════════════════════════╝\n\n"
                    f"Just send any video URL to download! 🎬\n\n"
                    f"{CREDIT_LINE}"
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_kb(),
            )
        return

    if data.startswith("q_"):
        quality = data[2:]
        if quality == "cancel":
            context.user_data.pop("pending_url", None)
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                user.id,
                f"❌ *Cancelled.* Send another link anytime!\n{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        url = context.user_data.pop("pending_url", None)
        if not url:
            await query.answer("⚠️ Session expired. Please send the link again.", show_alert=True)
            return

        q_labels = {
            "audio": "🎵 Audio Only",
            "360":   "📱 360p",
            "480":   "📺 480p",
            "720":   "🖥 720p HD",
            "1080":  "🖥 1080p FHD",
            "best":  "⚡ Best Quality",
        }
        platform  = detect_platform(url)
        short_url = url[:55] + "…" if len(url) > 55 else url

        await query.edit_message_text(
            f"⬇️ *Download Started!*\n\n"
            f"🌐 *Platform:* `{platform}`\n"
            f"🎯 *Quality:* `{q_labels.get(quality, quality)}`\n"
            f"🔗 *URL:* `{short_url}`\n\n"
            f"⏳ Please wait...\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )

        await _handle_download(update, context, url, quality, proc_msg=query.message)
        return

    if data == "how_to":
        await query.edit_message_text(
            f"📥 *How to Download*\n\n"
            "1️⃣ Copy a video link from any platform\n"
            "2️⃣ Paste it in this chat\n"
            "3️⃣ Choose your quality\n"
            "4️⃣ Your file arrives! 🎉\n\n"
            "⚡ No commands needed — just send the link!\n\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Close", callback_data="close_info")
            ]]),
        )
        return

    if data == "my_stats":
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id=?", (user.id,)
            ).fetchone()
        if row:
            uname = f"@{row['username']}" if row["username"] else "—"
            text  = (
                f"📊 *Your Statistics*\n\n"
                f"👤 *Name:* {row['first_name']}\n"
                f"📛 *Username:* {uname}\n"
                f"🆔 *User ID:* `{row['user_id']}`\n"
                f"📅 *Joined:* `{row['join_date'][:10]}`\n"
                f"🕐 *Last Active:* `{row['last_active'][:16]}`\n"
                f"📥 *Total Downloads:* `{row['downloads']}`\n"
                f"🚦 *Status:* {'🚫 Banned' if row['is_banned'] else '✅ Active'}\n"
                f"{CREDIT_LINE}"
            )
        else:
            text = f"❌ No stats found. Send /start first.\n{CREDIT_LINE}"
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Close", callback_data="close_info")
            ]]),
        )
        return

    if data == "supported":
        await query.edit_message_text(
            "🌐 *Supported Platforms*\n\n"
            "✅ YouTube (videos, Shorts)\n"
            "✅ Instagram (posts, Reels, Stories)\n"
            "✅ TikTok (videos)\n"
            "✅ Twitter / X (videos, GIFs)\n"
            "✅ Facebook (videos, Reels)\n"
            "✅ Reddit (videos)\n"
            "✅ Pinterest (videos)\n"
            "✅ Dailymotion\n"
            "✅ Vimeo\n"
            "✅ 1000+ more sites via yt-dlp!\n\n"
            "💡 Just send the URL — I'll handle the rest.\n\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Close", callback_data="close_info")
            ]]),
        )
        return

    if data == "support":
        context.user_data["awaiting_support"] = True
        await query.edit_message_text(
            "💬 *Contact Support*\n\n"
            "Send your message below.\n"
            "Our team will respond as soon as possible! 🙏\n\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_support")
            ]]),
        )
        return

    if data == "cancel_support":
        context.user_data.pop("awaiting_support", None)
        await query.edit_message_text(
            f"🏠 Welcome back, *{user.first_name}*!\nSend me a video link.\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Close", callback_data="close_info")
            ]]),
        )
        return

    if data == "our_channels":
        channels = get_all_channels()
        lines    = [f"• [{ch['channel_name']}]({channel_link(ch)})" for ch in channels]
        await query.edit_message_text(
            "👥 *Our Official Channels*\n\n" + "\n".join(lines) + f"\n\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Close", callback_data="close_info")
            ]]),
        )
        return

    if data == "close_info":
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if data == "bc_send":
        if not is_admin(user.id):
            await query.answer("❌ Admin only!", show_alert=True)
            return
        await query.edit_message_text("⏳ Starting broadcast...")
        await _execute_broadcast(
            context, user.id, "normal",
            bc_msg=context.bot_data.get("bc_msg"),
            buttons=context.bot_data.get("bc_buttons"),
            text_override=context.bot_data.pop("bc_text_override", None),
        )
        return

    if data == "bc_add_btn":
        if not is_admin(user.id):
            return
        context.user_data["bc_add_button"] = True
        await query.edit_message_text(
            "🔘 *Add Inline Buttons*\n\nSend buttons in this format (one per line):\n\n"
            "```\nButton Name | https://link.com\n"
            "Another Btn | https://link2.com\n```\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data.startswith("upage_"):
        if not is_admin(user.id):
            return
        page = int(data.split("_")[1])
        msg  = await _build_users_msg(page)
        await query.edit_message_text(
            msg["text"], parse_mode=ParseMode.MARKDOWN, reply_markup=msg["kb"]
        )
        return

    if data.startswith("ban_"):
        if not is_admin(user.id):
            return
        uid = int(data.split("_")[1])
        ban_user(uid)
        await query.answer(f"✅ User {uid} banned!", show_alert=True)
        msg = await _build_users_msg(0)
        await query.edit_message_text(
            msg["text"], parse_mode=ParseMode.MARKDOWN, reply_markup=msg["kb"]
        )
        return

    if data.startswith("unban_"):
        if not is_admin(user.id):
            return
        uid = int(data.split("_")[1])
        unban_user(uid)
        await query.answer(f"✅ User {uid} unbanned!", show_alert=True)
        msg = await _build_users_msg(0)
        await query.edit_message_text(
            msg["text"], parse_mode=ParseMode.MARKDOWN, reply_markup=msg["kb"]
        )
        return

    if data.startswith("rmch_"):
        if not is_admin(user.id):
            return
        ch_id = data[5:].replace("AT_", "@")
        remove_channel(ch_id)
        await query.answer(f"✅ Removed {ch_id}", show_alert=True)
        channels = get_all_channels()
        if not channels:
            await query.edit_message_text("✅ All force-join channels removed.")
            return
        text    = "📋 *Force-Join Channels* — tap to remove:\n\n"
        buttons = []
        for ch in channels:
            text += f"• `{ch['channel_id']}` — {ch['channel_name']}\n"
            safe  = ch["channel_id"].replace("@", "AT_")
            buttons.append([InlineKeyboardButton(
                f"❌ Remove {ch['channel_name']}", callback_data=f"rmch_{safe}"
            )])
        text += f"\n{CREDIT_LINE}"
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    if data.startswith("repsup_"):
        if not is_admin(user.id):
            return
        target_uid = int(data.split("_")[1])
        context.user_data["replying_support"] = target_uid
        await query.answer("📝 Send your reply now.", show_alert=True)
        return

# ═══════════════════════════════════════════════════════════════════════
#  ✉️  ADMIN PANEL BUTTON HANDLER
# ═══════════════════════════════════════════════════════════════════════

async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              text: str) -> bool:
    uid = update.effective_user.id

    if text == "🔙 Back to Menu":
        context.user_data["in_admin_panel"] = False
        context.user_data["admin_state"]    = None
        await update.message.reply_text(
            f"🏠 *Main Menu*\nSend me any video link!\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb(),
        )
        return True

    if text == "🔙 Back to Admin":
        context.user_data["admin_state"] = None
        await update.message.reply_text(
            f"🛡 *Admin Panel*\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_menu_kb(),
        )
        return True

    if text == "📢 Broadcast":
        context.user_data["admin_state"] = "BC_MENU"
        await update.message.reply_text(
            f"📢 *Broadcast Panel*\nChoose broadcast type:\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=broadcast_menu_kb(),
        )
        return True

    if text == "📨 Normal Broadcast":
        context.user_data["admin_state"] = "WAIT_BC_NORMAL"
        await update.message.reply_text(
            "📨 *Normal Broadcast*\n\n"
            "Send the message you want to broadcast to all users.\n"
            "(Text, photo, video, voice, sticker — all supported!)\n\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if text == "🔘 Button Broadcast":
        context.user_data["admin_state"] = "WAIT_BC_BTN_MSG"
        await update.message.reply_text(
            f"🔘 *Button Broadcast — Step 1 of 2*\n\nSend the message to broadcast:\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if text == "💎 Premium Broadcast":
        context.user_data["admin_state"] = "WAIT_BC_PREMIUM"
        await update.message.reply_text(
            "💎 *Premium Broadcast*\n\n"
            "📌 *Forward* any message to broadcast.\n"
            "It will be forwarded to all users with the original\n"
            "'Forwarded from' header — preserving premium emojis!\n\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if text == "📊 Statistics":
        await _send_statistics(update.message)
        return True

    if text == "🚫 Ban User":
        context.user_data["admin_state"] = "WAIT_BAN"
        await update.message.reply_text(
            f"🚫 *Ban User*\n\nSend the *User ID* to ban:\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if text == "✅ Unban User":
        context.user_data["admin_state"] = "WAIT_UNBAN"
        await update.message.reply_text(
            f"✅ *Unban User*\n\nSend the *User ID* to unban:\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if text == "📡 Add Channel":
        context.user_data["admin_state"] = "WAIT_CH_ADD"
        await update.message.reply_text(
            "📡 *Add Force-Join Channel*\n\n"
            "Send the channel username or ID:\n\n"
            "Format: `@username` or `@username | Channel Name`\n\n"
            "⚠️ Bot must be admin in the channel!\n\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if text == "❌ Remove Channel":
        channels = get_all_channels()
        if not channels:
            await update.message.reply_text("📭 No channels configured.")
            return True
        text_msg = "📋 *Force-Join Channels* — tap to remove:\n\n"
        buttons  = []
        for ch in channels:
            text_msg += f"• `{ch['channel_id']}` — {ch['channel_name']}\n"
            safe      = ch["channel_id"].replace("@", "AT_")
            buttons.append([InlineKeyboardButton(
                f"❌ Remove {ch['channel_name']}", callback_data=f"rmch_{safe}"
            )])
        text_msg += f"\n{CREDIT_LINE}"
        await update.message.reply_text(
            text_msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return True

    if text == "👑 Add Admin":
        context.user_data["admin_state"] = "WAIT_ADD_ADMIN"
        current = "\n".join(f"• `{a}`" for a in get_all_admins())
        await update.message.reply_text(
            f"👑 *Add Admin*\n\nCurrent admins:\n{current}\n\n"
            f"Send the *User ID* of the new admin:\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if text == "➖ Remove Admin":
        context.user_data["admin_state"] = "WAIT_RM_ADMIN"
        current = "\n".join(f"• `{a}`" for a in get_all_admins())
        await update.message.reply_text(
            f"➖ *Remove Admin*\n\nCurrent admins:\n{current}\n\n"
            f"Send the *User ID* to remove:\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if text == "💌 Default Message":
        context.user_data["admin_state"] = "WAIT_DEF_MSG"
        cur = get_setting("default_msg") or "—"
        await update.message.reply_text(
            f"💌 *Default Welcome Message*\n\nCurrent:\n{cur}\n\n"
            f"Send the new welcome message (Markdown supported):\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if text == "📦 Extract DB":
        await send_db_extract(update.message)
        return True

    if text == "📥 Add Data":
        context.user_data["admin_state"] = "WAIT_ADD_DATA"
        await update.message.reply_text(
            f"📥 *Add Data / Recover DB*\n\n"
            "Send the `.db` SQLite backup file.\n"
            "Users from it will be merged into the bot database.\n\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if text == "👥 View Users":
        msg = await _build_users_msg(0)
        await update.message.reply_text(
            msg["text"], parse_mode=ParseMode.MARKDOWN, reply_markup=msg["kb"]
        )
        return True

    return False


async def process_admin_state(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               text: str, state: str) -> None:
    uid = update.effective_user.id

    if state == "WAIT_BC_NORMAL":
        context.user_data["admin_state"] = None
        users = get_broadcast_user_ids()
        prog  = await update.message.reply_text(
            f"📨 *Broadcasting to {len(users)} users...*\n{CREDIT_LINE}", parse_mode=ParseMode.MARKDOWN
        )
        await _execute_broadcast(
            context, uid, "normal",
            bc_msg=update.message,
        )
        await update.message.reply_text("🛡 Admin Panel", reply_markup=admin_menu_kb())
        return

    if state == "WAIT_BC_BTN_MSG":
        context.user_data["bc_msg_saved"]  = update.message
        context.user_data["admin_state"]   = "WAIT_BC_BTN_BTNS"
        await update.message.reply_text(
            "🔘 *Button Broadcast — Step 2 of 2*\n\n"
            "Send the inline buttons (one per line):\n\n"
            "```\nButton Name | https://link.com\n"
            "Another Btn | https://link2.com\n```\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if state == "WAIT_BC_BTN_BTNS":
        buttons = parse_inline_buttons(text)
        bc_msg  = context.user_data.pop("bc_msg_saved", None)
        context.user_data["admin_state"] = None
        if not buttons:
            await update.message.reply_text(
                f"❌ No valid buttons.\n\nFormat: `Button Name | https://url.com`\n{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        await _execute_broadcast(
            context, uid, "button",
            bc_msg=bc_msg,
            buttons=buttons,
        )
        await update.message.reply_text("🛡 Admin Panel", reply_markup=admin_menu_kb())
        return

    if state == "WAIT_BC_PREMIUM":
        fwd_from      = update.message.forward_from
        fwd_from_chat = update.message.forward_from_chat
        is_forwarded  = fwd_from is not None or fwd_from_chat is not None
        if not is_forwarded:
            await update.message.reply_text(
                f"⚠️ Please *forward* a message.\n"
                "The 'Forwarded from' header must be present.\n{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        context.user_data["admin_state"] = None
        await _execute_broadcast(
            context, uid, "premium",
            bc_msg=update.message,
            is_forward=True,
        )
        await update.message.reply_text("🛡 Admin Panel", reply_markup=admin_menu_kb())
        return

    if state == "WAIT_BAN":
        if text.strip().isdigit():
            ban_user(int(text.strip()))
            context.user_data["admin_state"] = None
            await update.message.reply_text(
                f"✅ User `{text.strip()}` banned!\n{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_menu_kb(),
            )
        else:
            await update.message.reply_text("❌ Invalid ID. Numbers only.")
        return

    if state == "WAIT_UNBAN":
        if text.strip().isdigit():
            unban_user(int(text.strip()))
            context.user_data["admin_state"] = None
            await update.message.reply_text(
                f"✅ User `{text.strip()}` unbanned!\n{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_menu_kb(),
            )
        else:
            await update.message.reply_text("❌ Invalid ID. Numbers only.")
        return

    if state == "WAIT_CH_ADD":
        parts = [p.strip() for p in text.split("|", 1)]
        ch_id = parts[0].strip()
        if not ch_id.startswith("@"):
            ch_id = "@" + ch_id
        ch_name = parts[1].strip() if len(parts) > 1 else ch_id[1:]
        try:
            chat = await context.bot.get_chat(ch_id)
            ch_name = chat.title or ch_name
        except Exception:
            pass
        add_channel(ch_id, ch_name, uid)
        context.user_data["admin_state"] = None
        await update.message.reply_text(
            f"✅ *Channel Added!*\n\n"
            f"📢 *Name:* {ch_name}\n"
            f"🆔 *ID:* `{ch_id}`\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_menu_kb(),
        )
        return

    if state == "WAIT_ADD_ADMIN":
        if text.strip().isdigit():
            add_admin_db(int(text.strip()), uid)
            context.user_data["admin_state"] = None
            await update.message.reply_text(
                f"✅ Admin `{text.strip()}` added!\n{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_menu_kb(),
            )
        else:
            await update.message.reply_text("❌ Invalid ID. Numbers only.")
        return

    if state == "WAIT_RM_ADMIN":
        if text.strip().isdigit():
            remove_admin_db(int(text.strip()))
            context.user_data["admin_state"] = None
            await update.message.reply_text(
                f"✅ Admin `{text.strip()}` removed!\n{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_menu_kb(),
            )
        else:
            await update.message.reply_text("❌ Invalid ID. Numbers only.")
        return

    if state == "WAIT_DEF_MSG":
        set_setting("default_msg", text)
        context.user_data["admin_state"] = None
        await update.message.reply_text(
            f"✅ *Default welcome message updated!*\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_menu_kb(),
        )
        return

    if state == "WAIT_ADD_DATA":
        if update.message.document:
            tg_file = await context.bot.get_file(update.message.document.file_id)
            raw     = await tg_file.download_as_bytearray()
            with open("_recover.db", "wb") as fp:
                fp.write(raw)
            try:
                src   = sqlite3.connect("_recover.db")
                dst   = get_db()
                added = 0
                for row in src.execute("SELECT * FROM users"):
                    try:
                        dst.execute(
                            "INSERT OR IGNORE INTO users"
                            " (user_id, username, first_name, last_name)"
                            " VALUES (?,?,?,?)",
                            (row[0], row[1] if len(row) > 1 else None,
                             row[2] if len(row) > 2 else "User",
                             row[3] if len(row) > 3 else None),
                        )
                        dst.commit()
                        added += 1
                    except Exception:
                        pass
                src.close()
                context.user_data["admin_state"] = None
                await update.message.reply_text(
                    f"✅ *Data Recovered!*\n🆕 Merged `{added}` users.\n{CREDIT_LINE}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=admin_menu_kb(),
                )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Error reading DB: `{e}`", parse_mode=ParseMode.MARKDOWN
                )
        else:
            await update.message.reply_text("❌ Please send a `.db` SQLite file.")
        return

# ═══════════════════════════════════════════════════════════════════════
#  💬  MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════════════

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user    = update.effective_user
    message = update.message
    if not message or not user:
        return

    register_user(user)

    if is_banned(user.id):
        await message.reply_text("🚫 You have been banned from this bot.")
        return

    text = message.text or ""

    admin_state = context.user_data.get("admin_state")
    if admin_state and is_admin(user.id):
        await process_admin_state(update, context, text, admin_state)
        return

    if context.user_data.get("bc_add_button") and is_admin(user.id):
        context.user_data.pop("bc_add_button")
        buttons = parse_inline_buttons(text)
        if buttons:
            context.bot_data["bc_buttons"] = buttons
            await message.reply_text(
                f"✅ *{len(buttons)} button(s) added!* Starting broadcast...\n{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
            )
            await _execute_broadcast(
                context, user.id, "button",
                bc_msg=context.bot_data.get("bc_msg"),
                buttons=buttons,
                text_override=context.bot_data.pop("bc_text_override", None),
            )
        else:
            await message.reply_text(
                f"❌ No valid buttons.\nFormat: `Button Name | https://url.com`\n{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    if context.user_data.get("replying_support") and is_admin(user.id):
        target_uid = context.user_data.pop("replying_support")
        try:
            await context.bot.send_message(
                target_uid,
                f"💬 *Reply from Support Team:*\n\n{text}\n{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
            )
            await message.reply_text("✅ Reply sent to user!")
            with get_db() as conn:
                conn.execute(
                    "UPDATE support_messages SET replied=1 WHERE user_id=? AND replied=0",
                    (target_uid,),
                )
        except Exception as e:
            await message.reply_text(f"❌ Could not send: {e}")
        return

    if is_admin(user.id) and context.user_data.get("in_admin_panel"):
        handled = await handle_admin_panel(update, context, text)
        if handled:
            return

    if text == "🔙 Back to Menu":
        context.user_data["in_admin_panel"] = False
        context.user_data["admin_state"]    = None
        await message.reply_text(
            f"🏠 *Main Menu* — Send me a video link!\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb(),
        )
        return

    if context.user_data.get("awaiting_support"):
        context.user_data.pop("awaiting_support")
        uname = f"@{user.username}" if user.username else "—"
        fwd   = (
            f"💬 *New Support Message*\n"
            f"{'─' * 28}\n"
            f"👤 *From:* [{user.first_name}](tg://user?id={user.id})\n"
            f"🆔 *ID:* `{user.id}`\n"
            f"📛 *Username:* {uname}\n"
            f"{'─' * 28}\n"
            f"📝 *Message:*\n{text or '[Media]'}\n"
            f"{CREDIT_LINE}\n"
            f"🕐 `{now_ist()}`"
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("↩️ Reply", callback_data=f"repsup_{user.id}")
        ]])
        for admin_id in get_all_admins():
            try:
                bot_msg = await context.bot.send_message(
                    admin_id, fwd, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO support_messages (user_id, message_id, bot_msg_id)"
                        " VALUES (?,?,?)",
                        (user.id, message.message_id, bot_msg.message_id),
                    )
            except Exception as e:
                logger.error(f"Support fwd error: {e}")
        await message.reply_text(
            f"✅ *Message sent to support!*\nWe'll get back to you soon 🙏\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if text == "📥 How to Download":
        await message.reply_text(
            f"📥 *How to Download*\n\n"
            "1️⃣ Copy a video link from any platform\n"
            "2️⃣ Paste it in this chat\n"
            "3️⃣ Select your quality\n"
            "4️⃣ Get your file! 🎉\n\n"
            "⚡ No commands needed — just send the link!\n\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if text == "📊 My Stats":
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id=?", (user.id,)
            ).fetchone()
        if row:
            uname = f"@{row['username']}" if row["username"] else "—"
            await message.reply_text(
                f"📊 *Your Stats*\n\n"
                f"👤 *Name:* {row['first_name']}\n"
                f"📛 *Username:* {uname}\n"
                f"🆔 *ID:* `{row['user_id']}`\n"
                f"📅 *Joined:* `{row['join_date'][:10]}`\n"
                f"📥 *Downloads:* `{row['downloads']}`\n"
                f"🚦 *Status:* {'🚫 Banned' if row['is_banned'] else '✅ Active'}\n"
                f"{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    if text == "🌐 Supported Sites":
        await message.reply_text(
            f"🌐 *Supported Platforms*\n\n"
            "✅ YouTube (videos, Shorts)\n"
            "✅ Instagram (posts, Reels, Stories)\n"
            "✅ TikTok\n"
            "✅ Twitter / X\n"
            "✅ Facebook\n"
            "✅ Reddit\n"
            "✅ Pinterest\n"
            "✅ Dailymotion\n"
            "✅ Vimeo\n"
            "✅ 1000+ more sites!\n\n"
            "💡 Just send the URL — I'll handle the rest.\n\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if text == "💬 Support":
        context.user_data["awaiting_support"] = True
        await message.reply_text(
            f"💬 *Contact Support*\n\n"
            "Send your message below and our team will reply ASAP! 🙏\n\n"
            f"{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if text == "👥 Our Channels":
        channels = get_all_channels()
        lines    = [f"• [{ch['channel_name']}]({channel_link(ch)})" for ch in channels]
        await message.reply_text(
            f"👥 *Our Official Channels*\n\n" + "\n".join(lines) + f"\n\n{CREDIT_LINE}",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return

    url = extract_url(text)
    if url:
        not_joined = await check_force_join(update, context)
        if not_joined:
            await message.reply_text(
                f"🔒 *Join our channels first to download!*\n{CREDIT_LINE}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=build_join_keyboard(not_joined),
            )
            return
        await show_quality_picker(update, context, url)
        return

    not_joined = await check_force_join(update, context)
    if not_joined:
        await message.reply_text(
            f"🔒 *Join our channels first!*\n{CREDIT_LINE}",
            reply_markup=build_join_keyboard(not_joined),
        )
        return
    await message.reply_text(
        f"🤔 *Send me a valid video URL to download!*\n\n"
        "Supported: YouTube, Instagram, TikTok, Twitter, Facebook, Reddit & more!\n\n"
        f"{CREDIT_LINE}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(),
    )

# ═══════════════════════════════════════════════════════════════════════
#  🚀  MAIN
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    init_db()
    logger.info("🚀 DarkX Downloader Bot starting...")

    builder = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(60)
        .read_timeout(300)
        .write_timeout(300)
        .pool_timeout(60)
    )

    if LOCAL_API_URL:
        builder = builder.base_url(f"{LOCAL_API_URL}/bot")
        logger.info(f"Using local Bot API server: {LOCAL_API_URL}")

    app = builder.build()

    app.add_handler(CommandHandler("start",         cmd_start))
    app.add_handler(CommandHandler("help",          cmd_help))
    app.add_handler(CommandHandler("admin",         cmd_admin))
    app.add_handler(CommandHandler("statistics",    cmd_statistics))
    app.add_handler(CommandHandler("darkchannel",   cmd_darkchannel))
    app.add_handler(CommandHandler("removechannel", cmd_removechannel))
    app.add_handler(CommandHandler("broadcast",     cmd_broadcast))
    app.add_handler(CommandHandler("users",         cmd_users))
    app.add_handler(CommandHandler("ban",           cmd_ban))
    app.add_handler(CommandHandler("unban",         cmd_unban))

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (
            filters.TEXT
            | filters.PHOTO
            | filters.VIDEO
            | filters.Document.ALL
            | filters.AUDIO
            | filters.VOICE
            | filters.Sticker.ALL
            | filters.FORWARDED
        ) & ~filters.COMMAND,
        message_handler,
    ))

    async def post_init(application):
        await application.bot.set_my_commands([
            BotCommand("start", "Start the bot"),
            BotCommand("help",  "Show help"),
            BotCommand("admin", "Open admin panel"),
        ])
        logger.info("Bot commands set ✅")

    app.post_init = post_init

    logger.info("Bot is running ✅  — polling for updates...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    logger.info("Bot stopped.")


if __name__ == "__main__":
    main()
