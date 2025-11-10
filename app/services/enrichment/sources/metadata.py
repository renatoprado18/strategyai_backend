"""
Website Metadata Source for IMENSIAH Enrichment

Extracts metadata from company websites including:
- Company name and description
- Meta tags (description, keywords)
- Technology stack detection
- Open Graph data

This is a FREE source with fast response time (<500ms).
Used in QUICK enrichment phase.

Created: 2025-01-09
Version: 1.0.0
"""

import time
import logging
from typing import Dict, Any, Optional, List
import httpx
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from .base import EnrichmentSource, SourceResult

logger = logging.getLogger(__name__)


class MetadataSource(EnrichmentSource):
    """
    Extract metadata from company websites.

    Capabilities:
    - Extract company name from title, og:site_name, or domain
    - Extract description from meta tags
    - Detect technology stack (React, Next.js, WordPress, etc.)
    - Extract meta keywords
    - Parse Open Graph data

    Performance: ~300-500ms
    Cost: $0.00 (free)

    Usage:
        source = MetadataSource()
        result = await source.enrich("techstart.com")
        print(result.data)
        # {
        #     "company_name": "TechStart",
        #     "description": "B2B SaaS platform...",
        #     "meta_keywords": ["saas", "automation"],
        #     "website_tech": ["React", "Next.js"]
        # }
    """

    # Technology detection patterns
    TECH_PATTERNS = {
        "React": [
            r'react',
            r'__NEXT_DATA__',
            r'_reactRoot',
        ],
        "Next.js": [
            r'__NEXT_DATA__',
            r'_next/static',
            r'next\.js',
        ],
        "WordPress": [
            r'wp-content',
            r'wp-includes',
            r'wordpress',
        ],
        "Vercel": [
            r'vercel',
            r'_vercel',
        ],
        "Shopify": [
            r'shopify',
            r'cdn\.shopify\.com',
        ],
        "Wix": [
            r'wix\.com',
            r'parastorage',
        ],
        "Webflow": [
            r'webflow',
        ],
        "Django": [
            r'django',
            r'csrfmiddlewaretoken',
        ],
        "Flask": [
            r'flask',
        ],
        "Vue.js": [
            r'vue\.js',
            r'__vue__',
        ],
        "Angular": [
            r'angular',
            r'ng-',
        ],
        "Bootstrap": [
            r'bootstrap',
        ],
        "Tailwind": [
            r'tailwind',
        ],
        "jQuery": [
            r'jquery',
        ],
    }

    def __init__(self):
        """Initialize metadata source (free, fast)"""
        super().__init__(name="metadata", cost_per_call=0.0)
        self.timeout = 10.0  # 10 second timeout
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    async def enrich(self, domain: str, **kwargs) -> SourceResult:
        """
        Extract metadata from website.

        Args:
            domain: Domain to scrape (e.g., "techstart.com")
            **kwargs: Additional parameters (unused)

        Returns:
            SourceResult with metadata
        """
        start_time = time.time()

        try:
            # Ensure domain has protocol
            if not domain.startswith(("http://", "https://")):
                url = f"https://{domain}"
            else:
                url = domain

            # Fetch website
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": self.user_agent},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            html_content = response.text.lower()

            # Extract metadata
            data = {
                "company_name": self._extract_company_name(soup, domain),
                "description": self._extract_description(soup),
                "meta_description": self._extract_meta_description(soup),
                "meta_keywords": self._extract_meta_keywords(soup),
                "website_tech": self._detect_technologies(
                    html_content, response.headers
                ),
                "logo_url": self._extract_logo(soup, url),
                "social_media": self._extract_social_media(soup),
            }

            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"[Metadata] Extracted from {domain} in {duration_ms}ms ({len(data)} fields)",
                extra={"component": "metadata", "domain": domain, "fields_extracted": len(data), "duration_ms": duration_ms},
            )

            return SourceResult(
                source_name=self.name,
                success=True,
                data=data,
                duration_ms=duration_ms,
                cost_usd=0.0,
            )

        except httpx.TimeoutException as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"[Metadata] Request timeout for {domain} after {duration_ms}ms",
                extra={"component": "metadata", "domain": domain, "duration_ms": duration_ms}
            )
            raise Exception(f"Request timeout after {self.timeout}s")

        except httpx.HTTPStatusError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"[Metadata] HTTP {e.response.status_code} error for {domain}",
                extra={"component": "metadata", "domain": domain, "status": e.response.status_code, "duration_ms": duration_ms}
            )
            raise Exception(f"HTTP {e.response.status_code}: {e.response.reason_phrase}")

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[Metadata] Unexpected error for {domain}: {str(e)}",
                exc_info=True,
                extra={"component": "metadata", "domain": domain, "duration_ms": duration_ms, "error_type": type(e).__name__}
            )
            raise

    def _extract_company_name(
        self, soup: BeautifulSoup, domain: str
    ) -> Optional[str]:
        """Extract company name from various sources"""
        # Try Open Graph site_name
        og_site_name = soup.find("meta", property="og:site_name")
        if og_site_name and og_site_name.get("content"):
            return og_site_name["content"].strip()

        # Try title tag (remove common suffixes)
        title = soup.find("title")
        if title and title.string:
            name = title.string.strip()
            # Remove common suffixes
            for suffix in [
                "- Home",
                "| Home",
                "- Official Website",
                "| Official Website",
            ]:
                if suffix.lower() in name.lower():
                    name = name.split(suffix)[0].strip()
            return name

        # Fallback to domain name (capitalize)
        domain_name = urlparse(domain).netloc or domain
        domain_name = domain_name.replace("www.", "").split(".")[0]
        return domain_name.title()

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company description (prefer og:description)"""
        # Try Open Graph description
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return og_desc["content"].strip()

        # Try meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"].strip()

        # Try first paragraph
        first_p = soup.find("p")
        if first_p and first_p.string:
            return first_p.string.strip()[:200]

        return None

    def _extract_meta_description(
        self, soup: BeautifulSoup
    ) -> Optional[str]:
        """Extract meta description tag"""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"].strip()
        return None

    def _extract_meta_keywords(
        self, soup: BeautifulSoup
    ) -> Optional[List[str]]:
        """Extract meta keywords"""
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords and meta_keywords.get("content"):
            keywords = meta_keywords["content"].strip()
            # Split by comma and clean
            return [
                k.strip()
                for k in keywords.split(",")
                if k.strip()
            ][:10]  # Limit to 10
        return None

    def _detect_technologies(
        self, html_content: str, headers: Dict[str, str]
    ) -> List[str]:
        """Detect technologies used on the website"""
        detected = []

        # Check HTML content patterns
        for tech, patterns in self.TECH_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, html_content, re.IGNORECASE):
                    detected.append(tech)
                    break  # Only add once

        # Check server headers
        server = headers.get("server", "").lower()
        if "nginx" in server:
            detected.append("Nginx")
        elif "apache" in server:
            detected.append("Apache")
        elif "cloudflare" in server:
            detected.append("Cloudflare")

        # Check X-Powered-By header
        powered_by = headers.get("x-powered-by", "").lower()
        if "php" in powered_by:
            detected.append("PHP")
        elif "asp.net" in powered_by:
            detected.append("ASP.NET")

        # Remove duplicates and return
        return list(set(detected))

    def _extract_logo(
        self, soup: BeautifulSoup, base_url: str
    ) -> Optional[str]:
        """Extract logo URL"""
        # Try Open Graph image
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            logo = og_image["content"]
            if logo.startswith("http"):
                return logo
            elif logo.startswith("/"):
                return f"{base_url.rstrip('/')}{logo}"

        # Try favicon
        favicon = soup.find("link", rel="icon") or soup.find(
            "link", rel="shortcut icon"
        )
        if favicon and favicon.get("href"):
            logo = favicon["href"]
            if logo.startswith("http"):
                return logo
            elif logo.startswith("/"):
                return f"{base_url.rstrip('/')}{logo}"

        return None

    def _extract_social_media(
        self, soup: BeautifulSoup
    ) -> Optional[Dict[str, str]]:
        """Extract social media links"""
        social = {}

        # Common social media patterns
        patterns = {
            "linkedin": r"linkedin\.com/company/([^/\s\"]+)",
            "twitter": r"twitter\.com/([^/\s\"]+)",
            "facebook": r"facebook\.com/([^/\s\"]+)",
            "instagram": r"instagram\.com/([^/\s\"]+)",
        }

        # Find all links
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            for platform, pattern in patterns.items():
                match = re.search(pattern, href, re.IGNORECASE)
                if match and platform not in social:
                    social[platform] = href
                    break

        return social if social else None
