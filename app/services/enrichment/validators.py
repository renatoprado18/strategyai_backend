"""
Field Validators for Progressive Enrichment

Provides real-time validation for phone numbers, WhatsApp,
social media handles, and other form fields.
"""

import re
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================================================
# VALIDATION RESULT MODELS
# ============================================================================


class ValidationResult(BaseModel):
    """Generic validation result"""

    is_valid: bool
    formatted_value: Optional[str] = None
    error_message: Optional[str] = None
    suggestions: list[str] = []
    confidence: float = 100.0  # 0-100


# ============================================================================
# PHONE NUMBER VALIDATION (BRAZILIAN FORMAT)
# ============================================================================


class PhoneValidator:
    """Brazilian phone number validator"""

    # Regex patterns
    MOBILE_PATTERN = re.compile(r"^\+?55\s?\(?(\d{2})\)?\s?9\s?(\d{4})[- ]?(\d{4})$")
    LANDLINE_PATTERN = re.compile(r"^\+?55\s?\(?(\d{2})\)?\s?(\d{4})[- ]?(\d{4})$")

    @staticmethod
    def validate(phone: str) -> ValidationResult:
        """
        Validate Brazilian phone number

        Accepts formats:
        - +55 (11) 99999-9999  (mobile)
        - +55 11 9 9999-9999
        - 11999999999
        - (11) 3333-4444  (landline)

        Returns:
            ValidationResult with formatted number
        """
        if not phone or not phone.strip():
            return ValidationResult(
                is_valid=False,
                error_message="Telefone não pode estar vazio"
            )

        # Remove all non-digit characters
        digits_only = re.sub(r"\D", "", phone)

        # Check length
        if len(digits_only) < 10:
            return ValidationResult(
                is_valid=False,
                error_message="Telefone muito curto (mínimo 10 dígitos)"
            )

        if len(digits_only) > 13:
            return ValidationResult(
                is_valid=False,
                error_message="Telefone muito longo"
            )

        # Try to extract components
        # Mobile: +55 (DDD) 9 XXXX-XXXX = 13 digits
        # Landline: +55 (DDD) XXXX-XXXX = 12 digits

        if digits_only.startswith("55"):
            # Has country code
            digits_only = digits_only[2:]  # Remove country code

        if len(digits_only) == 11:  # Mobile: DDD + 9XXXX-XXXX
            ddd = digits_only[:2]
            number = digits_only[2:]

            if number[0] != "9":
                return ValidationResult(
                    is_valid=False,
                    error_message="Celular deve começar com 9"
                )

            formatted = f"+55 ({ddd}) {number[0]} {number[1:5]}-{number[5:]}"

            return ValidationResult(
                is_valid=True,
                formatted_value=formatted,
                confidence=95.0
            )

        elif len(digits_only) == 10:  # Landline: DDD + XXXX-XXXX
            ddd = digits_only[:2]
            number = digits_only[2:]

            formatted = f"+55 ({ddd}) {number[:4]}-{number[4:]}"

            return ValidationResult(
                is_valid=True,
                formatted_value=formatted,
                confidence=90.0
            )

        else:
            return ValidationResult(
                is_valid=False,
                error_message=f"Formato inválido ({len(digits_only)} dígitos)",
                suggestions=[
                    "Formato esperado: (11) 99999-9999 ou (11) 3333-4444"
                ]
            )


# ============================================================================
# SOCIAL MEDIA VALIDATORS
# ============================================================================


class InstagramValidator:
    """Instagram handle validator"""

    # Instagram usernames: 1-30 chars, letters, numbers, periods, underscores
    HANDLE_PATTERN = re.compile(r"^[A-Za-z0-9._]{1,30}$")

    @staticmethod
    def validate(handle: str) -> ValidationResult:
        """
        Validate Instagram handle

        Accepts:
        - @username
        - username
        - https://instagram.com/username
        - https://www.instagram.com/username

        Returns:
            ValidationResult with clean handle and formatted URL
        """
        if not handle or not handle.strip():
            return ValidationResult(
                is_valid=True,  # Optional field
                formatted_value=None
            )

        handle = handle.strip()

        # Extract username from URL
        if "instagram.com/" in handle:
            parts = handle.split("instagram.com/")
            if len(parts) == 2:
                handle = parts[1].rstrip("/")

        # Remove @ prefix
        if handle.startswith("@"):
            handle = handle[1:]

        # Validate format
        if not InstagramValidator.HANDLE_PATTERN.match(handle):
            return ValidationResult(
                is_valid=False,
                error_message="Handle inválido. Use apenas letras, números, pontos e underscores.",
                suggestions=[
                    "Exemplo: @empresa",
                    "Exemplo: empresa.oficial"
                ]
            )

        # Format as URL
        formatted_url = f"https://instagram.com/{handle}"

        return ValidationResult(
            is_valid=True,
            formatted_value=formatted_url,
            confidence=85.0
        )


class TikTokValidator:
    """TikTok handle validator"""

    # TikTok usernames: 2-24 chars, letters, numbers, periods, underscores
    HANDLE_PATTERN = re.compile(r"^[A-Za-z0-9._]{2,24}$")

    @staticmethod
    def validate(handle: str) -> ValidationResult:
        """
        Validate TikTok handle

        Accepts:
        - @username
        - username
        - https://tiktok.com/@username
        - https://www.tiktok.com/@username

        Returns:
            ValidationResult with clean handle and formatted URL
        """
        if not handle or not handle.strip():
            return ValidationResult(
                is_valid=True,  # Optional field
                formatted_value=None
            )

        handle = handle.strip()

        # Extract username from URL
        if "tiktok.com/" in handle:
            parts = handle.split("tiktok.com/")
            if len(parts) == 2:
                username_part = parts[1].rstrip("/")
                # Remove @ if present in URL
                if username_part.startswith("@"):
                    username_part = username_part[1:]
                handle = username_part

        # Remove @ prefix
        if handle.startswith("@"):
            handle = handle[1:]

        # Validate format
        if not TikTokValidator.HANDLE_PATTERN.match(handle):
            return ValidationResult(
                is_valid=False,
                error_message="Handle inválido. Use apenas letras, números, pontos e underscores (2-24 caracteres).",
                suggestions=[
                    "Exemplo: @minhaempresa",
                    "Exemplo: empresa.oficial"
                ]
            )

        # Format as URL
        formatted_url = f"https://www.tiktok.com/@{handle}"

        return ValidationResult(
            is_valid=True,
            formatted_value=formatted_url,
            confidence=85.0
        )


class LinkedInValidator:
    """LinkedIn URL validator"""

    COMPANY_PATTERN = re.compile(r"^https?://(www\.)?linkedin\.com/company/([A-Za-z0-9\-]+)/?$")
    PROFILE_PATTERN = re.compile(r"^https?://(www\.)?linkedin\.com/in/([A-Za-z0-9\-]+)/?$")

    @staticmethod
    def validate(url: str, expected_type: str = "company") -> ValidationResult:
        """
        Validate LinkedIn URL

        Args:
            url: LinkedIn URL
            expected_type: 'company' or 'profile'

        Returns:
            ValidationResult with formatted URL
        """
        if not url or not url.strip():
            return ValidationResult(
                is_valid=True,  # Optional field
                formatted_value=None
            )

        url = url.strip()

        # Ensure https://
        if not url.startswith("http"):
            # Assume user typed just the slug
            if expected_type == "company":
                url = f"https://linkedin.com/company/{url}"
            else:
                url = f"https://linkedin.com/in/{url}"

        # Normalize www
        url = url.replace("http://", "https://")
        if "www.linkedin.com" not in url:
            url = url.replace("linkedin.com", "www.linkedin.com")

        # Validate pattern
        if expected_type == "company":
            match = LinkedInValidator.COMPANY_PATTERN.match(url)
            if not match:
                return ValidationResult(
                    is_valid=False,
                    error_message="URL de empresa LinkedIn inválida",
                    suggestions=[
                        "Formato esperado: https://linkedin.com/company/nome-da-empresa"
                    ]
                )
        else:
            match = LinkedInValidator.PROFILE_PATTERN.match(url)
            if not match:
                return ValidationResult(
                    is_valid=False,
                    error_message="URL de perfil LinkedIn inválida",
                    suggestions=[
                        "Formato esperado: https://linkedin.com/in/nome-pessoa"
                    ]
                )

        return ValidationResult(
            is_valid=True,
            formatted_value=url,
            confidence=95.0
        )


# ============================================================================
# URL VALIDATOR
# ============================================================================


class URLValidator:
    """Website URL validator with auto-prefix"""

    URL_PATTERN = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE
    )

    @staticmethod
    def validate_and_format(url: str) -> ValidationResult:
        """
        Validate URL and auto-prefix with https:// if missing

        Args:
            url: User's input

        Returns:
            ValidationResult with formatted URL
        """
        if not url or not url.strip():
            return ValidationResult(
                is_valid=False,
                error_message="URL não pode estar vazia"
            )

        url = url.strip()

        # Remove trailing slash
        url = url.rstrip("/")

        # Auto-prefix with https:// if missing
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        # Validate format
        if not URLValidator.URL_PATTERN.match(url):
            return ValidationResult(
                is_valid=False,
                error_message="URL inválida",
                suggestions=[
                    "Exemplo: https://minhaempresa.com.br",
                    "Exemplo: minhaempresa.com"
                ]
            )

        return ValidationResult(
            is_valid=True,
            formatted_value=url,
            confidence=100.0
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def validate_phone(phone: str) -> ValidationResult:
    """Validate Brazilian phone number"""
    return PhoneValidator.validate(phone)


def validate_instagram(handle: str) -> ValidationResult:
    """Validate Instagram handle"""
    return InstagramValidator.validate(handle)


def validate_tiktok(handle: str) -> ValidationResult:
    """Validate TikTok handle"""
    return TikTokValidator.validate(handle)


def validate_linkedin_company(url: str) -> ValidationResult:
    """Validate LinkedIn company URL"""
    return LinkedInValidator.validate(url, expected_type="company")


def validate_linkedin_profile(url: str) -> ValidationResult:
    """Validate LinkedIn profile URL"""
    return LinkedInValidator.validate(url, expected_type="profile")


def validate_url(url: str) -> ValidationResult:
    """Validate and format website URL"""
    return URLValidator.validate_and_format(url)
