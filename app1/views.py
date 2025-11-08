# app1/jsonrpc.py
import uuid
import random
import hashlib
import json
import traceback
from datetime import datetime
from decimal import Decimal
import requests

from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from jsonrpcserver import method, dispatch, Error
from jsonrpcserver.result import Success

from .models import BankCard, Transfer
from .utils import send_telegram, get_error_response  # ⚡ errors.py dan olamiz


def expiry_matches(bankcard: BankCard, expiry_str: str) -> bool:
    """expiry_str: MM/YY"""
    if not expiry_str or not hasattr(bankcard, "expiry_date") or not bankcard.expiry_date:
        return False
    try:
        mm, yy = map(int, expiry_str.split("/"))
        return bankcard.expiry_date.month == mm and (bankcard.expiry_date.year % 100) == yy
    except Exception:
        return False


# --- Transfer yaratish ---
@method(name="transfer.create")
def transfer_create(**params):
    try:
        sender_num = str(params.get("sender_card_number", "")).replace(" ", "")
        receiver_num = str(params.get("receiver_card_number", "")).replace(" ", "")
        sender_expiry = params.get("sender_card_expiry")
        sending_amount = params.get("sending_amount")
        currency = int(params.get("currency", 860))  # 860=UZS, 840=USD, 643=RUB

        if not sender_num or not receiver_num or sending_amount is None or not sender_expiry:
            return get_error_response(32713)

        try:
            amount = Decimal(str(sending_amount))
            if amount <= 0:
                raise ValueError
        except Exception:
            return get_error_response(32709)

        sender = BankCard.objects.filter(card_number=sender_num).first()
        receiver = BankCard.objects.filter(card_number=receiver_num).first()

        if not sender or not receiver:
            return get_error_response(32701)

        if sender.status != "active" or receiver.status != "active":
            return get_error_response(32705)

        # ✅ YANGI QO‘SHILGAN QISM — expiry muddati tekshiruvi
        from datetime import date
        if not expiry_matches(sender, sender_expiry):
            return get_error_response(32704)  # Karta muddati noto‘g‘ri

        # 🔁 Kurs olish (faqat kerak bo‘lganda)
        currency_map = {840: "USD", 643: "RUB", 860: "UZS"}
        code = currency_map.get(currency)

        amount_in_uzs = amount
        if currency in [840, 643]:
            try:
                response = requests.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/", timeout=10)
                data = response.json()
                rate = next((Decimal(item["Rate"]) for item in data if item["Ccy"] == code), None)
                if not rate:
                    return get_error_response(32707)
                amount_in_uzs = amount * rate
            except Exception as e:
                return get_error_response(32706)

        if sender.balance < amount_in_uzs:
            return get_error_response(32702)

        # 🔐 OTP tayyorlash
        ext_id = f"tr-{uuid.uuid4()}"
        otp_plain = f"{random.randint(0, 999999):06d}"
        otp_hash = hashlib.sha256(otp_plain.encode()).hexdigest()

        transfer = Transfer.objects.create(
            ext_id=ext_id,
            sender=sender,
            receiver=receiver,
            sending_amount=amount_in_uzs,
            receiving_amount=amount_in_uzs,
            currency=currency,
            state="created",
        )

        cache.set(f"transfer_otp_{ext_id}", otp_hash, timeout=300)
        cache.set(f"transfer_tries_{ext_id}", 0, timeout=300)

        send_telegram(f"🔐 OTP: {otp_plain}\n🆔 {ext_id}")

        return Success({
            "ext_id": ext_id,
            "state": "created",
            "otp_sent": True,
            "amount_in_uzs": str(amount_in_uzs),
        })

    except Exception as e:
        traceback.print_exc()
        return get_error_response(32706)


# --- Transfer tasdiqlash ---
@method(name="transfer.confirm")
def transfer_confirm(**params):
    try:
        ext_id = params.get("ext_id")
        otp = str(params.get("otp", "")).strip()
        if not ext_id or not otp:
            return get_error_response(32713)

        transfer = Transfer.objects.select_related("sender", "receiver").filter(ext_id=ext_id).first()
        if not transfer:
            return get_error_response(32706)

        if transfer.state != "created":
            return get_error_response(32714)

        otp_hash = cache.get(f"transfer_otp_{ext_id}")
        tries = cache.get(f"transfer_tries_{ext_id}", 0)

        if otp_hash is None:
            return get_error_response(32710)
        if tries >= 3:
            return get_error_response(32711)
        if hashlib.sha256(otp.encode()).hexdigest() != otp_hash:
            cache.set(f"transfer_tries_{ext_id}", tries + 1, timeout=300)
            return get_error_response(32712)

        with transaction.atomic():
            transfer = Transfer.objects.select_for_update().get(ext_id=ext_id)
            if transfer.state != "created":
                return get_error_response(32714)

            sender = transfer.sender
            receiver = transfer.receiver

            if sender.balance < transfer.sending_amount:
                return get_error_response(32702)

            sender.balance -= transfer.sending_amount
            receiver.balance += transfer.receiving_amount
            sender.save(update_fields=['balance'])
            receiver.save(update_fields=['balance'])

            transfer.state = "confirmed"
            transfer.confirmed_at = datetime.now()
            transfer.save(update_fields=['state', 'confirmed_at'])

        try:
            send_telegram(f"✅ Transfer tasdiqlandi!\n🆔 {transfer.ext_id}\nFrom: {sender.card_number[-4:]}\nTo: {receiver.card_number[-4:]}")
        except Exception:
            pass

        cache.delete(f"transfer_otp_{ext_id}")
        cache.delete(f"transfer_tries_{ext_id}")

        return Success({
            "ext_id": transfer.ext_id,
            "state": transfer.state,
            "message": "Transfer muvaffaqiyatli yakunlandi"
        })

    except Exception as e:
        traceback.print_exc()
        return get_error_response(32706)


# --- Django view dispatcher ---
@csrf_exempt
def jsonrpc_view(request):
    if request.method == 'POST':
        try:
            body = request.body.decode()
            result = dispatch(body)
            if isinstance(result, str):
                result = json.loads(result)
            return JsonResponse(result, safe=False)
        except Exception:
            traceback.print_exc()
            return JsonResponse(get_error_response(32706), safe=False, status=500)

    return JsonResponse({'message': 'Only POST allowed'}, status=405)
