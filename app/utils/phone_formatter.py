"""
Phone number formatting utilities
Handles Brazilian phone number formatting and WhatsApp number extraction
"""
import re
from typing import Optional


def format_brazilian_phone(phone: str) -> str:
    """
    Format Brazilian phone number to standard format: +55 XX XXXXX-XXXX

    Args:
        phone: Phone number in various formats

    Returns:
        Formatted phone number
    """
    if not phone:
        return ""

    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Handle different input formats
    if digits.startswith('55'):
        # Already has country code
        digits = digits[2:]  # Remove country code temporarily

    if len(digits) < 10:
        # Invalid phone number
        return phone  # Return original

    # Extract parts
    if len(digits) == 11:
        # Mobile: (XX) 9XXXX-XXXX
        area_code = digits[:2]
        first_part = digits[2:7]
        second_part = digits[7:11]
    elif len(digits) == 10:
        # Landline: (XX) XXXX-XXXX
        area_code = digits[:2]
        first_part = digits[2:6]
        second_part = digits[6:10]
    else:
        # Invalid length
        return phone

    # Format as: +55 XX XXXXX-XXXX or +55 XX XXXX-XXXX
    return f"+55 {area_code} {first_part}-{second_part}"


def extract_whatsapp_number(url_or_number: str) -> str:
    """
    Extract phone number from WhatsApp link or format WhatsApp number

    Args:
        url_or_number: WhatsApp URL (wa.me/...) or phone number

    Returns:
        Formatted phone number
    """
    if not url_or_number:
        return ""

    # Extract from wa.me link
    if 'wa.me' in url_or_number:
        match = re.search(r'wa\.me/(\d+)', url_or_number)
        if match:
            number = match.group(1)
            return format_brazilian_phone(number)

    # Direct phone number
    return format_brazilian_phone(url_or_number)


def validate_brazilian_phone(phone: str) -> bool:
    """
    Validate if phone number is a valid Brazilian number

    Args:
        phone: Phone number to validate

    Returns:
        True if valid Brazilian phone number
    """
    if not phone:
        return False

    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Remove country code if present
    if digits.startswith('55'):
        digits = digits[2:]

    # Valid if 10 or 11 digits
    if len(digits) not in [10, 11]:
        return False

    # Check area code (first 2 digits should be valid)
    area_code = int(digits[:2])
    valid_area_codes = range(11, 100)  # Brazilian area codes

    return area_code in valid_area_codes


def is_whatsapp_link(text: str) -> bool:
    """
    Check if text contains a WhatsApp link

    Args:
        text: Text to check

    Returns:
        True if contains wa.me link
    """
    return 'wa.me' in text.lower() if text else False


def format_international_phone(phone: str, country_code: str = "55") -> str:
    """
    Format phone number with international country code

    Args:
        phone: Phone number
        country_code: Country code (default: 55 for Brazil)

    Returns:
        Phone number with country code
    """
    if not phone:
        return ""

    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Add country code if not present
    if not digits.startswith(country_code):
        digits = f"{country_code}{digits}"

    return f"+{digits}"
