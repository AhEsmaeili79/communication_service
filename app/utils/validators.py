import re
from typing import Optional
from email_validator import validate_email as email_validator, EmailNotValidError


class PhoneValidator:
    """Centralized phone number validation utility"""

    # Phone number patterns for different formats
    PATTERNS = [
        r'^\+98[0-9]{10}$',      # +98xxxxxxxxxx (Iran international)
        r'^0098[0-9]{10}$',      # 0098xxxxxxxxxx (Iran international with 00)
        r'^98[0-9]{10}$',        # 98xxxxxxxxxx (Iran without + or 00)
        r'^98[0-9]{11}$',        # 98xxxxxxxxxxx (Iran without + or 00 - 12 digits total)
        r'^09[0-9]{9}$',         # 09xxxxxxxxx (Iran local - 11 digits total)
        r'^09[0-9]{10}$',        # 09xxxxxxxxxx (Iran local - 12 digits total)
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
    def convert_phone_for_melipayamak(phone: str) -> str:

        clean_phone = PhoneValidator.clean_phone_number(phone)
        
        # Convert 98xxxxxxxxxx to 09xxxxxxxxx (Iranian mobile: 98 + 10 digits = 12 chars total)
        if re.match(r'^98[0-9]{10}$', clean_phone):
            # For Iranian mobile numbers: 989xxxxxxxxx should become 09xxxxxxxxx
            # Remove 989 prefix and add 09 prefix: '09' + digits[3:]
            return '09' + clean_phone[3:]
        
        # For 98xxxxxxxxxxx format (11 digits after 98), return as is
        # This format works directly with Melipayamak API
        if re.match(r'^98[0-9]{11}$', clean_phone):
            return clean_phone
        
        # Convert +98xxxxxxxxxx to 09xxxxxxxxx
        if re.match(r'^\+98[0-9]{10}$', clean_phone):
            # For +989xxxxxxxxx, remove +98 and add 09: '09' + digits[1:]
            return '09' + clean_phone[4:]
        
        # Convert 0098xxxxxxxxxx to 09xxxxxxxxx
        if re.match(r'^0098[0-9]{10}$', clean_phone):
            # For 00989xxxxxxxxx, remove 0098 and add 09: '09' + digits[1:]
            return '09' + clean_phone[5:]
        
        # If already in 09xxxxxxxxx format, return as is
        if re.match(r'^09[0-9]{9}$', clean_phone):
            return clean_phone
        
        # Handle 09xxxxxxxxxx format (12 digits total) - remove last digit
        if re.match(r'^09[0-9]{10}$', clean_phone):
            return clean_phone[:-1]
        
        # For other formats, return as is (let validation handle it)
        return clean_phone

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


class EmailValidator:
    """Centralized email validation utility"""

    @staticmethod
    def validate_email(email: str, field_name: str = "email address") -> str:
        """Validate email address, raise ValueError if invalid"""
        try:
            validated_email = email_validator(email)
            return validated_email.email
        except EmailNotValidError as e:
            raise ValueError(f"Invalid {field_name}: {str(e)}")

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Check if email address is valid"""
        try:
            email_validator(email)
            return True
        except EmailNotValidError:
            return False
