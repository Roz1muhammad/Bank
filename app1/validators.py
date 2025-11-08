import re
from datetime import date, datetime
from django.core.exceptions import ValidationError
from .models import BankCard



def luhn_check(card_number):

    if not card_number:
        raise ValidationError("Card number is missing.")

    card_number = str(card_number).replace(" ", "")
    if not card_number.isdigit():
        raise ValidationError("Card number must contain only digits.")

    total = 0
    reverse_digits = card_number[::-1]

    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n

    if total % 10 != 0:
        raise ValidationError("Invalid card number (Luhn check failed).")

    return True



def validate_card_number(card_number):
    if not card_number:
        raise ValidationError("Card number is missing.")
    if BankCard.objects.filter(card_number=card_number).exists():
        raise ValidationError("Card number already exists.")
    luhn_check(card_number)

def validate_expiry_date(expiry_date):
    if not expiry_date:
        raise ValidationError("Expiry date is missing.")

    try:
        if isinstance(expiry_date, str):
            expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        elif isinstance(expiry_date, datetime):
            expiry_date = expiry_date.date()
    except ValueError:
        raise ValidationError("Invalid expiry date format.")

    if expiry_date < date.today():
        raise ValidationError("Expiry date is in the past.")

    return expiry_date


def validate_phone(phone):
    if not phone:
        raise ValidationError("Phone number is missing.")
    if not re.match(r"^\+?\d{9,13}$", str(phone)):
        raise ValidationError("Invalid phone number format.")


def validate_balance(balance):
    try:
        balance = float(balance)
    except (ValueError, TypeError):
        raise ValidationError("Invalid balance format.")

    if balance <= 0:
        raise ValidationError("Balance must be greater than 0.")
