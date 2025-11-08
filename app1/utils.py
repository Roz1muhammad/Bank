import requests
import random
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from .models import Transfer


# --- 1. Telegramga xabar yuborish ---
def send_telegram(message: str):
    """
    Telegram bot orqali xabar yuboruvchi funksiya.
    .env yoki settings.py ichida quyidagi sozlamalar bo‘lishi kerak:
        TELEGRAM_BOT_TOKEN = 'your_bot_token'
        TELEGRAM_CHAT_ID = 'your_chat_id'
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

    if not token or not chat_id:
        print("⚠️ Telegram token yoki chat_id sozlanmagan!")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}

    try:
        resp = requests.post(url, data=payload, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegramga yuborishda xato: {e}")
        return False

import requests
import random
import hashlib
from django.conf import settings

# 🔹 Xato kodlar ro‘yxati
ERRORS = {
    32701: {"code": 32701, "message": "Invalid card number"},
    32702: {"code": 32702, "message": "Balance not enough"},
    32704: {"code": 32704, "message": "Invalid expiry or expired"},
    32705: {"code": 32705, "message": "Inactive card"},
    32706: {"code": 32706, "message": "Transfer not found"},
    32707: {"code": 32707, "message": "OTP expired"},
    32708: {"code": 32708, "message": "Too many attempts"},
    32709: {"code": 32709, "message": "Invalid OTP"},
    32710: {"code": 32710, "message": "Unexpected server error"},
    32713: {"code": 32713, "message": "Validation error"},
}


# --- 1. Xatolikni olish funksiyasi ---
def get_error_response(code: int):
    """
    Kod orqali mos xato xabarini qaytaradi.
    """
    return ERRORS.get(code, {"code": 32710, "message": "Unknown error"})


# --- 2. OTP yuborish ---
def send_otp(chat_id: int, otp: str) -> bool:
    """
    Telegram orqali OTP yuborish.
    """
    try:
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        if not token:
            print("⚠️ TELEGRAM_BOT_TOKEN sozlanmagan")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        text = f"🔐 Tasdiqlash kodi: <b>{otp}</b>"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        resp = requests.post(url, data=payload, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print("❌ OTP yuborishda xato:", e)
        return False


# --- 3. LUHN algoritmi ---
def luhn_check(card_number: str) -> bool:
    """
    Karta raqamini LUHN algoritmi bilan tekshiradi.
    """
    digits = [int(d) for d in str(card_number)]
    checksum = 0
    parity = len(digits) % 2

    for i, digit in enumerate(digits):
        if i % 2 == parity:
            digit *= 2
        if digit > 9:
            digit -= 9
        checksum += digit

    return checksum % 10 == 0


