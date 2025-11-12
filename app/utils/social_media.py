"""
Social media handle normalization utilities
Converts social media handles to full URLs
"""
import re
from typing import Optional


def normalize_instagram(handle: str) -> str:
    """
    Normalize Instagram handle to full URL

    Args:
        handle: Instagram handle (@username, username, or full URL)

    Returns:
        Full Instagram URL
    """
    if not handle:
        return ""

    handle = handle.strip()

    # Already a full URL
    if handle.startswith("http"):
        # Normalize to standard format
        handle = handle.replace("https://www.instagram.com/", "https://instagram.com/")
        handle = handle.rstrip("/")
        return handle

    # Remove @ if present
    if handle.startswith("@"):
        handle = handle[1:]

    # Build full URL
    return f"https://instagram.com/{handle}"


def normalize_tiktok(handle: str) -> str:
    """
    Normalize TikTok handle to full URL

    Args:
        handle: TikTok handle (@username, username, or full URL)

    Returns:
        Full TikTok URL
    """
    if not handle:
        return ""

    handle = handle.strip()

    # Already a full URL
    if handle.startswith("http"):
        handle = handle.replace("https://www.tiktok.com/", "https://tiktok.com/")
        handle = handle.rstrip("/")
        return handle

    # Add @ if not present
    if not handle.startswith("@"):
        handle = f"@{handle}"

    # Build full URL
    return f"https://tiktok.com/{handle}"


def normalize_linkedin(company_slug: str) -> str:
    """
    Normalize LinkedIn company slug to full URL

    Args:
        company_slug: LinkedIn company slug or full URL

    Returns:
        Full LinkedIn company URL
    """
    if not company_slug:
        return ""

    company_slug = company_slug.strip()

    # Already a full URL
    if company_slug.startswith("http"):
        company_slug = company_slug.replace("https://www.linkedin.com/", "https://linkedin.com/")
        company_slug = company_slug.rstrip("/")
        return company_slug

    # Remove leading @ or slashes
    company_slug = company_slug.lstrip("@/")

    # Build full URL
    return f"https://linkedin.com/company/{company_slug}"


def extract_social_handle(url: str, platform: str) -> Optional[str]:
    """
    Extract handle from social media URL

    Args:
        url: Social media URL
        platform: Platform name (instagram, tiktok, linkedin)

    Returns:
        Handle without URL or None if invalid
    """
    if not url or not platform:
        return None

    platform = platform.lower()

    if platform == "instagram":
        match = re.search(r'instagram\.com/([^/?]+)', url)
        return match.group(1) if match else None

    elif platform == "tiktok":
        match = re.search(r'tiktok\.com/(@[^/?]+)', url)
        return match.group(1) if match else None

    elif platform == "linkedin":
        match = re.search(r'linkedin\.com/company/([^/?]+)', url)
        return match.group(1) if match else None

    return None


def is_social_media_url(url: str) -> bool:
    """
    Check if URL is a social media link

    Args:
        url: URL to check

    Returns:
        True if URL is from a known social platform
    """
    if not url:
        return False

    social_domains = [
        'instagram.com',
        'tiktok.com',
        'linkedin.com',
        'facebook.com',
        'twitter.com',
        'x.com',
        'youtube.com'
    ]

    return any(domain in url.lower() for domain in social_domains)
