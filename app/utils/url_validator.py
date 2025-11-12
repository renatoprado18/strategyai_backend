"""
URL validation and normalization utilities
"""
import re
from urllib.parse import urlparse
from typing import Optional


def normalize_url(url: str) -> str:
    """
    Normalize URL by adding https:// prefix if missing

    Args:
        url: URL to normalize

    Returns:
        Normalized URL with protocol
    """
    if not url:
        return ""

    url = url.strip()

    # Already has protocol
    if url.startswith(('http://', 'https://', 'ftp://')):
        return url

    # Add https:// prefix
    return f"https://{url}"


def is_valid_url(url: str) -> bool:
    """
    Validate if string is a valid URL

    Args:
        url: URL to validate

    Returns:
        True if valid URL
    """
    if not url:
        return False

    url = url.strip()

    # Reject JavaScript and data URLs
    if url.startswith(('javascript:', 'data:', 'file:')):
        return False

    try:
        result = urlparse(url)
        # Must have scheme and netloc
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def extract_domain(url: str) -> Optional[str]:
    """
    Extract domain from URL

    Args:
        url: URL to extract domain from

    Returns:
        Domain name or None if invalid
    """
    if not url:
        return None

    try:
        parsed = urlparse(normalize_url(url))
        return parsed.netloc
    except Exception:
        return None


def is_brazilian_domain(url: str) -> bool:
    """
    Check if URL is a Brazilian domain (.com.br, .br)

    Args:
        url: URL to check

    Returns:
        True if Brazilian domain
    """
    domain = extract_domain(url)
    if not domain:
        return False

    return domain.endswith('.br')


def sanitize_url(url: str) -> str:
    """
    Sanitize URL to prevent injection attacks

    Args:
        url: URL to sanitize

    Returns:
        Sanitized URL
    """
    if not url:
        return ""

    url = url.strip()

    # Remove whitespace
    url = re.sub(r'\s+', '', url)

    # Normalize protocol
    url = normalize_url(url)

    # Validate
    if not is_valid_url(url):
        raise ValueError(f"Invalid URL: {url}")

    return url


def get_url_metadata(url: str) -> dict:
    """
    Extract metadata from URL

    Args:
        url: URL to analyze

    Returns:
        Dictionary with URL metadata
    """
    normalized_url = normalize_url(url)
    parsed = urlparse(normalized_url)

    return {
        "scheme": parsed.scheme,
        "domain": parsed.netloc,
        "path": parsed.path,
        "is_brazilian": is_brazilian_domain(url),
        "is_secure": parsed.scheme == "https"
    }
