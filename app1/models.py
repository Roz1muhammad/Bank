from django.db import models
from django.core.exceptions import ValidationError
from datetime import date, datetime
import re,uuid

STATUS_CHOICES = (
    ("active", "Active"),
    ("inactive", "Inactive"),
    ("expired", "Expired"),
)

class BankCard(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    card_number = models.CharField(max_length=16, unique=True)
    expiry_date = models.DateField()
    phone = models.CharField(max_length=16, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="inactive")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def save(self, *args, **kwargs):

        if not self.card_number:
            raise ValidationError("Karta raqami majburiy.")
        cn = str(self.card_number).replace(" ", "")
        if not cn.isdigit():
            raise ValidationError("Karta raqami faqat raqamlardan iborat bo‘lishi kerak.")
        if len(cn) != 16:
            raise ValidationError("Karta raqami 16 ta raqamdan iborat bo‘lishi kerak.")
        self.card_number = cn

        if not self.phone:
            raise ValidationError("Telefon raqam majburiy.")
        p = str(self.phone).strip()
        if not re.match(r'^\+998\d{9}$', p):
            raise ValidationError("Telefon raqam formati noto‘g‘ri. To‘g‘ri format: +998XXXXXXXXX")
        self.phone = p


        if self.balance is None:
            self.balance = 0
        try:
            if float(self.balance) < 0:
                raise ValidationError("Balans manfiy bo‘la olmaydi.")
        except (TypeError, ValueError):
            raise ValidationError("Balans formati noto‘g‘ri.")


        if not isinstance(self.expiry_date, date):
            raise ValidationError("Amal muddati noto‘g‘ri (sana bo‘lishi kerak).")

        if self.expiry_date < date.today():
            raise ValidationError("Kartaning amal muddati o‘tgan.")

      
        valid_status = [c[0] for c in STATUS_CHOICES]
        if self.status not in valid_status:
            raise ValidationError(f"Status noto‘g‘ri. Mavjud: {valid_status}")

        print("✅ Validatsiyadan o‘tdi va saqlanmoqda...")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.card_number} ({self.status})"
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
import uuid
import re

class Error(models.Model):
    code = models.IntegerField(unique=True)
    en = models.CharField(max_length=255)
    ru = models.CharField(max_length=255)
    uz = models.CharField(max_length=255)

    def __str__(self):
        return f"Error {self.code}: {self.en}"


class Transfer(models.Model):
    class State(models.TextChoices):
        CREATED = 'created', 'Yaratildi'
        CONFIRMED = 'confirmed', 'Tasdiqlandi'
        CANCELLED = 'cancelled', 'Bekor qilindi'

    ext_id = models.CharField(max_length=255, unique=True)
    sender = models.ForeignKey('BankCard', on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_transfers')
    receiver = models.ForeignKey('BankCard', on_delete=models.SET_NULL, null=True, blank=True, related_name='received_transfers')

    sending_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    currency = models.IntegerField(choices=((643, 'RUB'), (840, 'USD')))
    receiving_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.CREATED)
    try_count = models.IntegerField(default=0, validators=[MaxValueValidator(3)])
    otp = models.CharField(max_length=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Sender va Receiver mavjudligini tekshirish
        if not self.sender or not self.receiver:
            raise ValidationError("Ikkala karta ham ko‘rsatilishi kerak.")

        if len(self.sender.card_number) != 16 or len(self.receiver.card_number) != 16:
            raise ValidationError("Karta raqami 16 ta raqamdan iborat bo‘lishi kerak.")

        if self.currency not in (643, 840):
            raise ValidationError("Faqat 643 (RUB) va 840 (USD) valyutalar ruxsat etilgan.")

    def save(self, *args, **kwargs):
        if not self.ext_id:
            self.ext_id = f"tr-{uuid.uuid4()}"
        if not self.receiving_amount:
            self.receiving_amount = self.sending_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transfer {self.ext_id}: {self.state}"

