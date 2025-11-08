from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import BankCard, Transfer, Error
from .utils import send_telegram


# === Yordamchi funksiya (safe localtime) ===
def safe_localtime(dt):
    """Agar datetime timezone-naive bo‘lsa, uni o‘zgartirmay qaytaradi"""
    if not dt:
        return None
    if timezone.is_naive(dt):
        return dt
    return timezone.localtime(dt)


# === 1. Yangi karta yaratilganda Telegramga xabar yuborish ===
@receiver(post_save, sender=BankCard)
def send_telegram_on_new_card(sender, instance, created, **kwargs):
    if created:
        msg = (
            f"🆕 <b>Yangi karta qo‘shildi!</b>\n"
            f"💳 <b>Karta:</b> {instance.card_number}\n"
            f"📅 <b>Muddati:</b> {instance.expiry_date}\n"
            f"📞 <b>Telefon:</b> {instance.phone or 'yo‘q'}\n"
            f"💰 <b>Balans:</b> {instance.balance} UZS\n"
            f"📌 <b>Status:</b> {instance.status}"
        )
        send_telegram(msg)


# === 2. Transfer holatlari uchun signal ===
@receiver(post_save, sender=Transfer)
def send_telegram_on_transfer(sender, instance, created, **kwargs):
    """
    Transfer modeli yangilanganda holatga qarab Telegram xabar yuboradi.
    🔹 Endi faqat tasdiqlangan (confirmed) transferlar haqida xabar boradi.
    """
    try:
        # 🟢 Yangi yaratilganda hech narsa yuborilmaydi (faqat OTP jsonrpcdan ketadi)
        if created:
            return

        # 🔵 Tasdiqlangan (state == 'confirmed')
        if instance.state == "confirmed":
            msg = (
                f"✅ <b>Transfer tasdiqlandi!</b>\n"
                f"🆔 <b>Ext ID:</b> {instance.ext_id}\n"
                f"💳 <b>Jo‘natuvchi:</b> {instance.sender.card_number}\n"
                f"💳 <b>Qabul qiluvchi:</b> {instance.receiver.card_number}\n"
                f"💰 <b>Summa:</b> {instance.sending_amount} ({instance.currency})\n"
                f"⏰ <b>Tasdiqlangan:</b> {safe_localtime(instance.confirmed_at).strftime('%Y-%m-%d %H:%M:%S')}"
            )
            send_telegram(msg)

        # 🔴 Xatolik holati
        elif instance.state == "error":
            try:
                err = Error.objects.get(code=instance.error_code)
                reason = f"{err.uz} ({err.en})"
            except Error.DoesNotExist:
                reason = "Noma’lum xatolik"

            msg = (
                f"⚠️ <b>Transfer xato bilan yakunlandi!</b>\n"
                f"🆔 <b>Ext ID:</b> {instance.ext_id}\n"
                f"💳 <b>Jo‘natuvchi:</b> {instance.sender.card_number}\n"
                f"💳 <b>Qabul qiluvchi:</b> {instance.receiver.card_number}\n"
                f"💰 <b>Summa:</b> {instance.sending_amount} ({instance.currency})\n"
                f"❌ <b>Xato kodi:</b> {instance.error_code}\n"
                f"📄 <b>Sabab:</b> {reason}"
            )
            send_telegram(msg)

    except Exception as e:
        print("Telegram signal xatolik:", e)
