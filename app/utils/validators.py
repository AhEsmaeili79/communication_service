import re
from typing import Optional


class PhoneValidator:
    """Centralized phone number validation utility"""

    # Phone number patterns for different formats
    PATTERNS = [
        r'^\+98[0-9]{10}$',      # +98xxxxxxxxxx (Iran international)
        r'^0098[0-9]{10}$',      # 0098xxxxxxxxxx (Iran international with 00)
        r'^09[0-9]{9}$',         # 09xxxxxxxxx (Iran local)
        r'^5000[0-9]{10}$',     # 5000xxxxxxxxxx (Iran SMS sender)
        r'^\+?[1-9]\d{1,14}$'    # General international format
    ]

    @staticmethod
    def clean_phone_number(phone: str) -> str:
        """Clean phone number by removing formatting characters"""
        return re.sub(r'[\s\-\(\)]', '', phone)

    @staticmethod
    def is_valid_phone_number(phone: str) -> bool:
        """Validate phone number format"""
        clean_phone = PhoneValidator.clean_phone_number(phone)
        return any(re.match(pattern, clean_phone) for pattern in PhoneValidator.PATTERNS)

    @staticmethod
    def validate_phone_number(phone: str, field_name: str = "phone number") -> str:
        """Validate and clean phone number, raise ValueError if invalid"""
        clean_phone = PhoneValidator.clean_phone_number(phone)
        if not PhoneValidator.is_valid_phone_number(clean_phone):
            raise ValueError(f"Invalid {field_name} format: {phone}")
        return clean_phone


def validate_sms_text(text: str) -> str:
    """Validate and clean SMS text"""
    if not text or not text.strip():
        raise ValueError("SMS text cannot be empty")

    cleaned_text = text.strip()
    if len(cleaned_text) > 1600:
        raise ValueError("SMS text exceeds maximum length of 1600 characters")

    return cleaned_text
