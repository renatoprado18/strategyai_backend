"""Utility modules for the IMENSIAH platform"""

from .social_media import (
    normalize_instagram,
    normalize_tiktok,
    normalize_linkedin,
    extract_social_handle,
    is_social_media_url
)

from .phone_formatter import (
    format_brazilian_phone,
    extract_whatsapp_number,
    validate_brazilian_phone,
    is_whatsapp_link,
    format_international_phone
)

from .url_validator import (
    normalize_url,
    is_valid_url,
    extract_domain,
    is_brazilian_domain,
    sanitize_url,
    get_url_metadata
)

__all__ = [
    # Social media
    'normalize_instagram',
    'normalize_tiktok',
    'normalize_linkedin',
    'extract_social_handle',
    'is_social_media_url',
    # Phone
    'format_brazilian_phone',
    'extract_whatsapp_number',
    'validate_brazilian_phone',
    'is_whatsapp_link',
    'format_international_phone',
    # URL
    'normalize_url',
    'is_valid_url',
    'extract_domain',
    'is_brazilian_domain',
    'sanitize_url',
    'get_url_metadata',
]
