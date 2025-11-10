"""
Unit tests for field translation (backend → frontend).

Tests the translate_fields_for_frontend() function that maps
backend snake_case and ai_prefixed fields to frontend camelCase.
"""

import pytest
from app.routes.enrichment_progressive import translate_fields_for_frontend


class TestFieldTranslation:
    """Test field name translation for frontend compatibility"""

    def test_critical_layer1_translations(self):
        """Test Layer 1 critical fixes (company_name → name, region → state)"""
        backend_data = {
            "company_name": "Google",
            "region": "São Paulo",
            "city": "São Paulo",
            "country": "BR",
            "timezone": "America/Sao_Paulo"
        }

        result = translate_fields_for_frontend(backend_data)

        # CRITICAL FIX: User was manually entering company name
        assert result["name"] == "Google"
        assert "company_name" not in result

        # CRITICAL FIX: User was manually entering state
        assert result["state"] == "São Paulo"
        assert "region" not in result

        # These should pass through unchanged
        assert result["city"] == "São Paulo"
        assert result["country"] == "BR"
        assert result["timezone"] == "America/Sao_Paulo"

    def test_ai_prefix_removal(self):
        """Test AI field prefix removal (ai_industry → industry)"""
        backend_data = {
            "ai_industry": "Technology",
            "ai_company_size": "10001+",
            "ai_digital_maturity": "Advanced",
            "ai_target_audience": "Businesses",
            "ai_key_differentiators": "Innovation"
        }

        result = translate_fields_for_frontend(backend_data)

        # All ai_ prefixes should be removed
        assert result["industry"] == "Technology"
        assert result["companySize"] == "10001+"
        assert result["digitalMaturity"] == "Advanced"
        assert result["targetAudience"] == "Businesses"
        assert result["keyDifferentiators"] == "Innovation"

        # No ai_ prefixed keys should remain
        assert not any(key.startswith("ai_") for key in result.keys())

    def test_snake_to_camel_case(self):
        """Test snake_case to camelCase conversion"""
        backend_data = {
            "employee_count": "25-50",
            "annual_revenue": "$10M-$50M",
            "legal_name": "Google LLC",
            "founded_year": 1998,
            "website_tech": ["React", "Next.js"],
            "meta_description": "Search engine",
            "logo_url": "https://example.com/logo.png",
            "place_id": "ChIJ123ABC"
        }

        result = translate_fields_for_frontend(backend_data)

        assert result["employeeCount"] == "25-50"
        assert result["annualRevenue"] == "$10M-$50M"
        assert result["legalName"] == "Google LLC"
        assert result["foundedYear"] == 1998
        assert result["websiteTech"] == ["React", "Next.js"]
        assert result["metaDescription"] == "Search engine"
        assert result["logoUrl"] == "https://example.com/logo.png"
        assert result["placeId"] == "ChIJ123ABC"

    def test_fields_without_translation_pass_through(self):
        """Test that fields without translation mappings pass through unchanged"""
        backend_data = {
            "domain": "google.com",
            "location": "São Paulo, SP",
            "phone": "+55 11 1234-5678",
            "email": "contact@example.com"
        }

        result = translate_fields_for_frontend(backend_data)

        # These should remain unchanged
        assert result["domain"] == "google.com"
        assert result["location"] == "São Paulo, SP"
        assert result["phone"] == "+55 11 1234-5678"
        assert result["email"] == "contact@example.com"

    def test_empty_data(self):
        """Test translation with empty data"""
        result = translate_fields_for_frontend({})
        assert result == {}

    def test_none_values_preserved(self):
        """Test that None values are preserved"""
        backend_data = {
            "company_name": None,
            "ai_industry": None,
            "employee_count": None
        }

        result = translate_fields_for_frontend(backend_data)

        assert result["name"] is None
        assert result["industry"] is None
        assert result["employeeCount"] is None

    def test_complete_layer1_response(self):
        """Test complete Layer 1 data translation (real-world scenario)"""
        layer1_backend = {
            "company_name": "TechStart Innovations",
            "description": "B2B SaaS platform for startups",
            "meta_description": "Innovative tech solutions",
            "meta_keywords": ["saas", "automation"],
            "website_tech": ["React", "Next.js", "Vercel"],
            "logo_url": "https://techstart.com/logo.png",
            "social_media": {"linkedin": "https://linkedin.com/company/techstart"},
            "country": "BR",
            "country_name": "Brazil",
            "region": "São Paulo",
            "city": "São Paulo",
            "timezone": "America/Sao_Paulo",
            "isp": "Google LLC",
            "ip_address": "8.8.8.8",
            "ip_location": "São Paulo, São Paulo, Brazil",
            "domain": "techstart.com"
        }

        result = translate_fields_for_frontend(layer1_backend)

        # Critical translations
        assert result["name"] == "TechStart Innovations"
        assert result["state"] == "São Paulo"

        # CamelCase conversions
        assert result["metaDescription"] == "Innovative tech solutions"
        assert result["metaKeywords"] == ["saas", "automation"]
        assert result["websiteTech"] == ["React", "Next.js", "Vercel"]
        assert result["logoUrl"] == "https://techstart.com/logo.png"
        assert result["socialMedia"] == {"linkedin": "https://linkedin.com/company/techstart"}
        assert result["countryName"] == "Brazil"
        assert result["ipAddress"] == "8.8.8.8"
        assert result["ipLocation"] == "São Paulo, São Paulo, Brazil"

        # Pass-through fields
        assert result["description"] == "B2B SaaS platform for startups"
        assert result["country"] == "BR"
        assert result["city"] == "São Paulo"
        assert result["timezone"] == "America/Sao_Paulo"
        assert result["isp"] == "Google LLC"
        assert result["domain"] == "techstart.com"

    def test_complete_layer3_response(self):
        """Test complete Layer 3 data translation (AI + all layers)"""
        layer3_backend = {
            # Layer 1 data
            "company_name": "TechStart",
            "region": "São Paulo",
            "city": "São Paulo",

            # Layer 2 data
            "employee_count": "25-50",
            "annual_revenue": "$1M-$10M",
            "legal_name": "TechStart Innovations LTDA",

            # Layer 3 data (AI inference)
            "ai_industry": "Technology / SaaS",
            "ai_company_size": "25-50",
            "ai_digital_maturity": "Advanced",
            "ai_target_audience": "B2B Startups",
            "ai_key_differentiators": "Automation & AI"
        }

        result = translate_fields_for_frontend(layer3_backend)

        # All translations should be applied
        assert result["name"] == "TechStart"
        assert result["state"] == "São Paulo"
        assert result["city"] == "São Paulo"
        assert result["employeeCount"] == "25-50"
        assert result["annualRevenue"] == "$1M-$10M"
        assert result["legalName"] == "TechStart Innovations LTDA"
        assert result["industry"] == "Technology / SaaS"
        assert result["companySize"] == "25-50"
        assert result["digitalMaturity"] == "Advanced"
        assert result["targetAudience"] == "B2B Startups"
        assert result["keyDifferentiators"] == "Automation & AI"

        # No backend field names should remain
        assert "company_name" not in result
        assert "region" not in result
        assert "employee_count" not in result
        assert not any(key.startswith("ai_") for key in result.keys())

    def test_mixed_translated_and_untranslated_fields(self):
        """Test data with both translated and untranslated fields"""
        backend_data = {
            "company_name": "Example Inc",  # Needs translation
            "domain": "example.com",         # No translation
            "ai_industry": "Finance",         # Needs translation
            "phone": "+1234567890",           # No translation
            "employee_count": "100-250",      # Needs translation
            "email": "info@example.com"       # No translation
        }

        result = translate_fields_for_frontend(backend_data)

        # Translated
        assert result["name"] == "Example Inc"
        assert result["industry"] == "Finance"
        assert result["employeeCount"] == "100-250"

        # Untranslated (pass-through)
        assert result["domain"] == "example.com"
        assert result["phone"] == "+1234567890"
        assert result["email"] == "info@example.com"

        # Original names should not exist
        assert "company_name" not in result
        assert "ai_industry" not in result
        assert "employee_count" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
