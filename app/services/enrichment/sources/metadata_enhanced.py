"""
Enhanced Metadata Source with Intelligence

Extends the base MetadataSource with:
- Enhanced structured data extraction (JSON-LD, Open Graph)
- Social media profile detection (Instagram, TikTok, LinkedIn)
- Contact information extraction (WhatsApp, phone)
- Logo extraction from multiple sources
- Improved technology detection

Layer: 1 (Free, <2s)
"""

import logging
import re
import json
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from .metadata import MetadataSource
from .base import SourceResult

logger = logging.getLogger(__name__)


class EnhancedMetadataSource(MetadataSource):
    """
    Enhanced metadata extraction with intelligence.

    New capabilities beyond base MetadataSource:
    - JSON-LD structured data parsing
    - Enhanced Open Graph extraction
    - Social media profile detection (Instagram, TikTok, LinkedIn)
    - Contact information extraction (WhatsApp, phone)
    - Multiple logo source detection
    - Enhanced technology detection

    Performance: ~400-600ms
    Cost: $0.00 (free)
    """

    # Social media regex patterns
    SOCIAL_PATTERNS = {
        "instagram": [
            r'instagram\.com/([a-zA-Z0-9._]+)',
            r'@([a-zA-Z0-9._]+)',  # In text
        ],
        "tiktok": [
            r'tiktok\.com/@([a-zA-Z0-9._]+)',
            r'tiktok\.com/([a-zA-Z0-9._]+)',
        ],
        "linkedin_company": [
            r'linkedin\.com/company/([a-zA-Z0-9-]+)',
        ],
        "linkedin_founder": [
            r'linkedin\.com/in/([a-zA-Z0-9-]+)',
        ],
        "facebook": [
            r'facebook\.com/([a-zA-Z0-9._]+)',
        ],
        "twitter": [
            r'twitter\.com/([a-zA-Z0-9_]+)',
            r'x\.com/([a-zA-Z0-9_]+)',
        ],
        "youtube": [
            r'youtube\.com/@([a-zA-Z0-9_-]+)',
            r'youtube\.com/c/([a-zA-Z0-9_-]+)',
            r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
        ],
    }

    # Contact patterns
    CONTACT_PATTERNS = {
        "whatsapp": [
            r'wa\.me/(\d+)',
            r'api\.whatsapp\.com/send\?phone=(\d+)',
        ],
        "phone": [
            r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
        ],
        "email": [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        ],
    }

    def __init__(self):
        """Initialize enhanced metadata source"""
        super().__init__()
        self.name = "metadata_enhanced"

    async def enrich(self, domain: str, **kwargs) -> SourceResult:
        """
        Extract enhanced metadata from website.

        This extends the base MetadataSource.enrich() with additional intelligence.
        """
        # Get base metadata first
        base_result = await super().enrich(domain, **kwargs)

        if not base_result.success:
            return base_result

        # Add enhanced intelligence
        try:
            # Re-fetch for enhanced parsing (we need the soup object)
            if not domain.startswith(("http://", "https://")):
                url = f"https://{domain}"
            else:
                url = domain

            import httpx
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": self.user_agent},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            html_content = response.text

            # Enhanced extractions
            enhanced_data = {
                **base_result.data,  # Keep base metadata
                **self._extract_structured_data(soup),
                **self._extract_social_media_enhanced(soup, html_content),
                **self._extract_contact_info(soup, html_content),
                "logo_url": self._extract_logo_enhanced(soup, url),
            }

            # Remove None values
            enhanced_data = {k: v for k, v in enhanced_data.items() if v is not None and v != {}}

            logger.info(
                f"[Metadata Enhanced] Extracted {len(enhanced_data)} fields from {domain}",
                extra={
                    "component": "metadata_enhanced",
                    "domain": domain,
                    "fields_count": len(enhanced_data),
                }
            )

            return SourceResult(
                source_name=self.name,
                success=True,
                data=enhanced_data,
                duration_ms=base_result.duration_ms,
                cost_usd=0.0,
            )

        except Exception as e:
            logger.warning(
                f"[Metadata Enhanced] Failed to enhance metadata for {domain}: {e}",
                exc_info=True
            )
            # Return base result if enhancement fails
            return base_result

    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract JSON-LD structured data.

        Looks for:
        - Organization schema
        - LocalBusiness schema
        - Corporation schema
        """
        structured_data = {}

        # Find all JSON-LD scripts
        json_ld_scripts = soup.find_all("script", type="application/ld+json")

        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)

                # Handle both single object and array
                if isinstance(data, list):
                    items = data
                else:
                    items = [data]

                for item in items:
                    schema_type = item.get("@type", "")

                    # Organization/LocalBusiness/Corporation
                    if schema_type in ["Organization", "LocalBusiness", "Corporation"]:
                        if item.get("name"):
                            structured_data["company_name"] = item["name"]
                        if item.get("description"):
                            structured_data["description"] = item["description"]
                        if item.get("logo"):
                            structured_data["logo_url"] = item["logo"]
                        if item.get("telephone"):
                            structured_data["phone"] = item["telephone"]
                        if item.get("address"):
                            addr = item["address"]
                            if isinstance(addr, dict):
                                if addr.get("addressLocality"):
                                    structured_data["city"] = addr["addressLocality"]
                                if addr.get("addressRegion"):
                                    structured_data["region"] = addr["addressRegion"]
                                if addr.get("addressCountry"):
                                    structured_data["country"] = addr["addressCountry"]
                        if item.get("sameAs"):
                            # Social media links in sameAs
                            same_as = item["sameAs"]
                            if isinstance(same_as, list):
                                for link in same_as:
                                    self._parse_social_link(link, structured_data)

            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.debug(f"Failed to parse JSON-LD: {e}")
                continue

        return structured_data

    def _extract_social_media_enhanced(
        self, soup: BeautifulSoup, html_content: str
    ) -> Dict[str, Any]:
        """
        Enhanced social media detection.

        Finds profiles in:
        - Footer links
        - Header navigation
        - Social media icon sections
        - Text content
        """
        social_media = {}

        # Find all links and text
        links = soup.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")
            self._parse_social_link(href, social_media)

        # Also scan raw HTML for patterns
        for platform, patterns in self.SOCIAL_PATTERNS.items():
            if platform not in social_media:
                for pattern in patterns:
                    match = re.search(pattern, html_content, re.IGNORECASE)
                    if match:
                        handle = match.group(1)
                        # Format as full URL
                        social_media[platform] = self._format_social_url(platform, handle)
                        break

        # Return nested dict for clarity
        return {"social_media": social_media} if social_media else {}

    def _parse_social_link(self, link: str, social_dict: Dict[str, str]):
        """Parse a link and extract social media handle"""
        for platform, patterns in self.SOCIAL_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, link, re.IGNORECASE)
                if match and platform not in social_dict:
                    handle = match.group(1)
                    social_dict[platform] = self._format_social_url(platform, handle)
                    return

    def _format_social_url(self, platform: str, handle: str) -> str:
        """Format social media handle as full URL"""
        handle = handle.strip("@/")

        url_formats = {
            "instagram": f"https://instagram.com/{handle}",
            "tiktok": f"https://tiktok.com/@{handle}",
            "linkedin_company": f"https://linkedin.com/company/{handle}",
            "linkedin_founder": f"https://linkedin.com/in/{handle}",
            "facebook": f"https://facebook.com/{handle}",
            "twitter": f"https://twitter.com/{handle}",
            "youtube": f"https://youtube.com/{handle}",
        }

        return url_formats.get(platform, f"https://{platform}.com/{handle}")

    def _extract_contact_info(
        self, soup: BeautifulSoup, html_content: str
    ) -> Dict[str, Any]:
        """
        Extract contact information.

        Finds:
        - WhatsApp links (wa.me)
        - Phone numbers
        - Email addresses
        """
        contacts = {}

        # WhatsApp
        for pattern in self.CONTACT_PATTERNS["whatsapp"]:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                contacts["whatsapp"] = f"+{match.group(1)}"
                break

        # Phone (look in footer or contact section)
        footer = soup.find("footer") or soup
        footer_text = footer.get_text()

        for pattern in self.CONTACT_PATTERNS["phone"]:
            match = re.search(pattern, footer_text)
            if match:
                phone = match.group(0)
                # Clean up phone number
                phone = re.sub(r'\s+', ' ', phone).strip()
                contacts["phone"] = phone
                break

        # Email (look in footer or mailto links)
        mailto_links = soup.find_all("a", href=re.compile(r'^mailto:', re.I))
        if mailto_links:
            email = mailto_links[0].get("href", "").replace("mailto:", "")
            contacts["email"] = email.split("?")[0]  # Remove query params

        return contacts

    def _extract_logo_enhanced(
        self, soup: BeautifulSoup, base_url: str
    ) -> Optional[str]:
        """
        Enhanced logo extraction from multiple sources.

        Priority:
        1. JSON-LD logo
        2. Open Graph image
        3. Apple touch icon
        4. Favicon
        5. <img> with "logo" in class/id
        """
        # 1. JSON-LD (already handled in structured data)

        # 2. Open Graph image
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            logo = og_image["content"]
            if logo.startswith("http"):
                return logo
            elif logo.startswith("/"):
                return f"{base_url.rstrip('/')}{logo}"

        # 3. Apple touch icon
        apple_icon = soup.find("link", rel=re.compile(r"apple-touch-icon", re.I))
        if apple_icon and apple_icon.get("href"):
            logo = apple_icon["href"]
            if logo.startswith("http"):
                return logo
            elif logo.startswith("/"):
                return f"{base_url.rstrip('/')}{logo}"

        # 4. Favicon
        favicon = soup.find("link", rel=re.compile(r"icon", re.I))
        if favicon and favicon.get("href"):
            logo = favicon["href"]
            if logo.startswith("http"):
                return logo
            elif logo.startswith("/"):
                return f"{base_url.rstrip('/')}{logo}"

        # 5. <img> with "logo" in class/id
        logo_imgs = soup.find_all("img", class_=re.compile(r"logo", re.I))
        if not logo_imgs:
            logo_imgs = soup.find_all("img", id=re.compile(r"logo", re.I))

        if logo_imgs:
            logo = logo_imgs[0].get("src", "")
            if logo.startswith("http"):
                return logo
            elif logo.startswith("/"):
                return f"{base_url.rstrip('/')}{logo}"

        return None
