# app_name/validators.py

import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

import re

def is_valid_phone_number(phone_number):
    """
    Validates that the phone number has exactly 10 digits.
    """
    phone_pattern = re.compile(r'^\d{10}$')
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


