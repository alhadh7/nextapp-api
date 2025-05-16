# app_name/validators.py

import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

def is_valid_phone_number(phone_number):
    """
    Validates that the phone number is in international format, e.g., +12345678901
    """
    phone_pattern = re.compile(r'^\+\d{10,15}$')
    return bool(phone_pattern.match(phone_number))

def is_valid_email(email):
    """
    Validates that the email address is properly formatted
    """
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False
