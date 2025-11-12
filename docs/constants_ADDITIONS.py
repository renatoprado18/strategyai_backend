"""
Constants to add to app/core/constants.py
"""

# ============================================================================
# FIELD TRANSLATION MAP (Backend → Frontend)
# ============================================================================

FIELD_TRANSLATION_MAP = {
    # Layer 1 (Metadata + IP API)
    "company_name": "name",
    "region": "state",
    "country_name": "countryName",
    "ip_address": "ipAddress",
    "ip_location": "ipLocation",

    # Layer 2 (Clearbit + ReceitaWS + Google)
    "employee_count": "employeeCount",
    "annual_revenue": "annualRevenue",
    "legal_name": "legalName",
    "reviews_count": "reviewsCount",

    # Layer 3 (AI Inference)
    "ai_industry": "industry",
    "ai_company_size": "companySize",
    "ai_digital_maturity": "digitalMaturity",
    "ai_target_audience": "targetAudience",
    "ai_key_differentiators": "keyDifferentiators",

    # Additional fields
    "founded_year": "foundedYear",
    "website_tech": "websiteTech",
    "meta_description": "metaDescription",
    "meta_keywords": "metaKeywords",
    "logo_url": "logoUrl",
    "social_media": "socialMedia",
    "place_id": "placeId",
}

# ============================================================================
# PROGRESSIVE ENRICHMENT TIMEOUTS
# ============================================================================

PROGRESSIVE_ENRICHMENT_MAX_WAIT_SECONDS = 30
PROGRESSIVE_ENRICHMENT_POLL_INTERVAL = 0.5

# ============================================================================
# CONFIDENCE THRESHOLDS
# ============================================================================

CONFIDENCE_THRESHOLD_LAYER1 = 70.0
CONFIDENCE_THRESHOLD_LAYER2 = 85.0
CONFIDENCE_THRESHOLD_LAYER3 = 75.0

# ============================================================================
# BASE CONFIDENCE SCORES BY FIELD
# ============================================================================

BASE_CONFIDENCE_SCORES = {
    # High confidence (government data)
    "cnpj": 95.0,
    "legal_name": 95.0,
    "registration_status": 95.0,

    # High confidence (verified sources)
    "place_id": 90.0,
    "rating": 90.0,
    "reviews_count": 90.0,
    "verified_address": 90.0,

    # Good confidence (B2B data)
    "employee_count": 85.0,
    "annual_revenue": 85.0,
    "founded_year": 85.0,

    # Moderate confidence (AI inference)
    "ai_industry": 75.0,
    "ai_company_size": 75.0,
    "ai_digital_maturity": 75.0,
    "ai_target_audience": 75.0,
    "ai_key_differentiators": 75.0,

    # Lower confidence (scraped data)
    "company_name": 70.0,
    "description": 70.0,
    "website_tech": 70.0,

    # Approximate data
    "ip_location": 60.0,
    "timezone": 60.0,

    # Default
    "default": 50.0,
}
