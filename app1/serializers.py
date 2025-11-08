from rest_framework import serializers
from .models import BankCard, Transfer


class TransferCreateSerializer(serializers.Serializer):
    sender_card_number = serializers.CharField()
    sender_card_expiry = serializers.CharField()
    receiver_card_number = serializers.CharField()
    sending_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()

    def validate(self, data):
        sender_num = str(data.get("sender_card_number", "")).replace(" ", "")
        receiver_num = str(data.get("receiver_card_number", "")).replace(" ", "")
        sender_expiry = data.get("sender_card_expiry")

        # Bo‘sh bo‘lishini tekshirish
        if not sender_num or not receiver_num:
            raise serializers.ValidationError("Karta raqamlari majburiy.")

        if sender_num == receiver_num:
            raise serializers.ValidationError("O‘zingizga pul yuborish mumkin emas.")

        # Sender mavjudligini tekshirish
        if not BankCard.objects.filter(card_number=sender_num).exists():
            raise serializers.ValidationError("Sender karta topilmadi.")

        # Receiver mavjudligini tekshirish
        if not BankCard.objects.filter(card_number=receiver_num).exists():
            raise serializers.ValidationError("Receiver karta topilmadi.")

        # Expiry formatini tekshirish
        import re
        if not re.match(r"^(0[1-9]|1[0-2])\/\d{2}$", sender_expiry or ""):
            raise serializers.ValidationError("Karta muddati noto‘g‘ri formatda (MM/YY bo‘lishi kerak).")

        # Balans va status check keyin view ichida qilinadi
        return data


class TransferConfirmSerializer(serializers.Serializer):
    ext_id = serializers.CharField()
    otp = serializers.CharField()

    def validate(self, data):
        ext_id = data.get("ext_id")
        otp = data.get("otp")

        if not ext_id:
            raise serializers.ValidationError("ext_id majburiy.")
        if not otp:
            raise serializers.ValidationError("OTP majburiy.")
        if len(otp) != 6 or not otp.isdigit():
            raise serializers.ValidationError("OTP 6 ta raqamdan iborat bo‘lishi kerak.")

        # Transfer mavjudligini viewda tekshiriladi (bu yerda faqat forma tekshiruv)
        return data
