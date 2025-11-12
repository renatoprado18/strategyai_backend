"""
Pydantic Models for IMENSIAH Data Enrichment System

Defines data structures for:
- Quick enrichment (sync - 2-3s)
- Deep enrichment (async - 30s+)
- Source attribution
- Quality metrics

Created: 2025-01-09
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class DataQualityTier(str, Enum):
    """Quality tier classification for enriched data"""

    MINIMAL = "minimal"  # <40% completeness
    MODERATE = "moderate"  # 40-70% completeness
    HIGH = "high"  # 70-90% completeness
    EXCELLENT = "excellent"  # >90% completeness


class SourceCallInfo(BaseModel):
    """
    Information about a single data source call.

    Tracks performance, cost, and outcome of each API call
    for transparency and debugging.
    """

    name: str = Field(..., description="Source name")
    success: bool = Field(..., description="Whether call succeeded")
    cost: float = Field(0.0, description="Cost in USD", ge=0)
    duration_ms: int = Field(..., description="Duration in milliseconds", ge=0)
    cached: bool = Field(False, description="Whether from cache")
    error_type: Optional[str] = Field(None, description="Error type if failed")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "clearbit",
                "success": True,
                "cost": 0.10,
                "duration_ms": 1200,
                "cached": False,
                "error_type": None,
            }
        }


class EnrichmentData(BaseModel):
    """
    Base enrichment data model.

    Contains common fields shared between quick and deep enrichment.
    """

    # Company identification
    company_name: Optional[str] = Field(None, description="Company legal name")
    domain: str = Field(..., description="Website domain")
    website: str = Field(..., description="Full website URL")

    # Basic info (usually from quick enrichment)
    description: Optional[str] = Field(None, description="Company description")
    industry: Optional[str] = Field(None, description="Industry/sector")
    location: Optional[str] = Field(
        None, description="Primary location (city, state)"
    )
    country: Optional[str] = Field(None, description="Country code (BR, US, etc)")

    # Technology (from metadata scraping)
    website_tech: Optional[List[str]] = Field(
        None, description="Technologies detected on website"
    )
    meta_description: Optional[str] = Field(
        None, description="Website meta description"
    )
    meta_keywords: Optional[List[str]] = Field(
        None, description="Website meta keywords"
    )

    # Source attribution (field → source mapping)
    source_attribution: Dict[str, str] = Field(
        default_factory=dict,
        description="Maps each field to its data source",
    )

    # Quality metrics
    completeness_score: Optional[float] = Field(
        None, description="Completeness percentage (0-100)", ge=0, le=100
    )
    confidence_score: Optional[float] = Field(
        None, description="Confidence percentage (0-100)", ge=0, le=100
    )
    data_quality_tier: Optional[DataQualityTier] = Field(
        None, description="Quality tier classification"
    )

    # Cost tracking
    total_cost_usd: float = Field(0.0, description="Total cost in USD", ge=0)
    sources_called: List[SourceCallInfo] = Field(
        default_factory=list, description="All sources called"
    )

    class Config:
        use_enum_values = True


class QuickEnrichmentData(EnrichmentData):
    """
    Quick enrichment data (sync - 2-3 seconds).

    Uses only fast/free sources:
    - Website metadata scraping
    - IP geolocation
    - Basic WHOIS data

    This data is returned immediately to provide a "wow" moment
    while deep enrichment runs in the background.
    """

    # IP/Location (from IP API)
    ip_location: Optional[str] = Field(None, description="Location from IP")
    timezone: Optional[str] = Field(None, description="Timezone")

    # Timestamps
    quick_completed_at: Optional[datetime] = Field(
        None, description="When quick enrichment completed"
    )
    quick_duration_ms: Optional[int] = Field(
        None, description="Quick enrichment duration", ge=0
    )

    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "TechStart Innovations",
                "domain": "techstart.com",
                "website": "https://techstart.com",
                "description": "B2B SaaS platform for enterprise automation",
                "industry": "Technology",
                "location": "São Paulo, SP",
                "country": "BR",
                "website_tech": ["React", "Next.js", "Vercel"],
                "meta_description": "Enterprise automation made simple",
                "ip_location": "São Paulo, Brazil",
                "timezone": "America/Sao_Paulo",
                "source_attribution": {
                    "company_name": "metadata",
                    "description": "metadata",
                    "website_tech": "metadata",
                    "ip_location": "ip_api",
                },
                "completeness_score": 45.0,
                "confidence_score": 70.0,
                "data_quality_tier": "moderate",
                "total_cost_usd": 0.00,
                "sources_called": [
                    {
                        "name": "metadata",
                        "success": True,
                        "cost": 0.00,
                        "duration_ms": 420,
                        "cached": False,
                    },
                    {
                        "name": "ip_api",
                        "success": True,
                        "cost": 0.00,
                        "duration_ms": 180,
                        "cached": False,
                    },
                ],
                "quick_completed_at": "2025-01-09T14:23:45Z",
                "quick_duration_ms": 2100,
            }
        }


class DeepEnrichmentData(EnrichmentData):
    """
    Deep enrichment data (async - 30+ seconds).

    Includes all quick enrichment fields plus data from:
    - Clearbit (company details, employee count)
    - ReceitaWS (Brazilian CNPJ data)
    - Google Places (location verification)
    - Proxycurl (LinkedIn data)

    This provides comprehensive company intelligence for
    strategic analysis and decision-making.
    """

    # Company details (from Clearbit)
    legal_name: Optional[str] = Field(None, description="Legal entity name")
    employee_count: Optional[str] = Field(
        None, description="Employee count range (e.g., '25-50')"
    )
    annual_revenue: Optional[str] = Field(
        None, description="Annual revenue range"
    )
    founded_year: Optional[int] = Field(None, description="Year founded")
    company_type: Optional[str] = Field(
        None, description="Company type (private, public, etc)"
    )

    # Brazilian data (from ReceitaWS)
    cnpj: Optional[str] = Field(None, description="Brazilian CNPJ number")
    cnae: Optional[str] = Field(
        None, description="CNAE code (industry classification)"
    )
    legal_nature: Optional[str] = Field(
        None, description="Legal nature (LTDA, SA, etc)"
    )
    registration_status: Optional[str] = Field(
        None, description="Registration status (active/inactive)"
    )
    registration_date: Optional[str] = Field(
        None, description="Registration date"
    )

    # Location details (from Google Places)
    address: Optional[str] = Field(None, description="Full address")
    phone: Optional[str] = Field(None, description="Phone number")
    place_id: Optional[str] = Field(None, description="Google Places ID")
    rating: Optional[float] = Field(None, description="Google rating", ge=0, le=5)
    reviews_count: Optional[int] = Field(
        None, description="Number of reviews", ge=0
    )

    # LinkedIn data (from Proxycurl)
    linkedin_url: Optional[str] = Field(None, description="LinkedIn company URL")
    linkedin_followers: Optional[int] = Field(
        None, description="LinkedIn followers", ge=0
    )
    linkedin_description: Optional[str] = Field(
        None, description="LinkedIn about section"
    )
    specialties: Optional[List[str]] = Field(
        None, description="Company specialties"
    )

    # Additional metadata
    logo_url: Optional[str] = Field(None, description="Company logo URL")
    social_media: Optional[Dict[str, str]] = Field(
        None, description="Social media profiles"
    )
    tags: Optional[List[str]] = Field(
        None, description="Industry tags/categories"
    )

    # NEW: Social media profiles (from enhanced metadata)
    instagram: Optional[str] = Field(None, description="Instagram profile URL")
    tiktok: Optional[str] = Field(None, description="TikTok profile URL")
    linkedin_company: Optional[str] = Field(None, description="LinkedIn company page")
    linkedin_founder: Optional[str] = Field(None, description="LinkedIn founder profile")
    facebook: Optional[str] = Field(None, description="Facebook page URL")
    twitter: Optional[str] = Field(None, description="Twitter/X profile URL")
    youtube: Optional[str] = Field(None, description="YouTube channel URL")

    # NEW: Contact information
    whatsapp: Optional[str] = Field(None, description="WhatsApp number")
    email: Optional[str] = Field(None, description="Contact email")

    # NEW: AI-inferred strategic insights
    ai_industry: Optional[str] = Field(None, description="AI-inferred industry")
    ai_target_audience: Optional[str] = Field(None, description="B2B/B2C/Both")
    ai_company_size: Optional[str] = Field(None, description="Micro/Pequena/Média/Grande")
    ai_digital_maturity: Optional[str] = Field(None, description="Baixa/Média/Alta")
    ai_communication_tone: Optional[str] = Field(None, description="Communication style")
    ai_key_differentiators: Optional[List[str]] = Field(
        None, description="Competitive advantages"
    )
    ai_strategic_focus: Optional[str] = Field(None, description="Strategic positioning")
    ai_opportunities: Optional[List[str]] = Field(
        None, description="Growth opportunities"
    )

    # Timestamps (extends QuickEnrichmentData)
    quick_completed_at: Optional[datetime] = Field(
        None, description="When quick enrichment completed"
    )
    quick_duration_ms: Optional[int] = Field(
        None, description="Quick enrichment duration", ge=0
    )
    deep_completed_at: Optional[datetime] = Field(
        None, description="When deep enrichment completed"
    )
    deep_duration_ms: Optional[int] = Field(
        None, description="Deep enrichment duration", ge=0
    )

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj(cls, v: Optional[str]) -> Optional[str]:
        """Validate and format CNPJ number"""
        if v:
            # Remove any non-digit characters
            digits = "".join(filter(str.isdigit, v))
            if len(digits) == 14:
                # Format as XX.XXX.XXX/XXXX-XX
                return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "TechStart Innovations",
                "legal_name": "TechStart Innovations LTDA",
                "domain": "techstart.com",
                "website": "https://techstart.com",
                "description": "B2B SaaS platform for enterprise automation",
                "industry": "Technology / SaaS",
                "location": "São Paulo, SP",
                "country": "BR",
                "employee_count": "25-50",
                "annual_revenue": "R$ 5-10M",
                "founded_year": 2019,
                "company_type": "Private",
                "cnpj": "12.345.678/0001-99",
                "cnae": "6201-5/00",
                "legal_nature": "LTDA",
                "registration_status": "Active",
                "address": "Av. Paulista, 1000 - Bela Vista, São Paulo - SP",
                "phone": "+55 11 1234-5678",
                "rating": 4.7,
                "reviews_count": 23,
                "linkedin_url": "https://linkedin.com/company/techstart",
                "linkedin_followers": 1247,
                "specialties": [
                    "Enterprise Automation",
                    "SaaS",
                    "Digital Transformation",
                ],
                "website_tech": ["React", "Next.js", "Vercel", "PostgreSQL"],
                "source_attribution": {
                    "company_name": "clearbit",
                    "employee_count": "clearbit",
                    "cnpj": "receita_ws",
                    "legal_nature": "receita_ws",
                    "address": "google_places",
                    "rating": "google_places",
                    "linkedin_url": "proxycurl",
                    "website_tech": "metadata",
                },
                "completeness_score": 94.0,
                "confidence_score": 89.0,
                "data_quality_tier": "excellent",
                "total_cost_usd": 0.12,
                "sources_called": [
                    {
                        "name": "metadata",
                        "success": True,
                        "cost": 0.00,
                        "duration_ms": 420,
                        "cached": False,
                    },
                    {
                        "name": "ip_api",
                        "success": True,
                        "cost": 0.00,
                        "duration_ms": 180,
                        "cached": False,
                    },
                    {
                        "name": "clearbit",
                        "success": True,
                        "cost": 0.10,
                        "duration_ms": 1200,
                        "cached": False,
                    },
                    {
                        "name": "receita_ws",
                        "success": True,
                        "cost": 0.00,
                        "duration_ms": 2800,
                        "cached": False,
                    },
                    {
                        "name": "google_places",
                        "success": True,
                        "cost": 0.02,
                        "duration_ms": 3100,
                        "cached": False,
                    },
                ],
                "quick_completed_at": "2025-01-09T14:23:45Z",
                "quick_duration_ms": 2100,
                "deep_completed_at": "2025-01-09T14:24:16Z",
                "deep_duration_ms": 31400,
            }
        }
