"""
Standalone Field Translation Test (No Dependencies)

Tests field translation logic without requiring FastAPI app or external services.
This validates the EXACT issue reported: backend field names not matching frontend.
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.routes.enrichment_progressive import translate_fields_for_frontend


def test_critical_layer1_translations():
    """
    TEST: Layer 1 critical fixes (company_name → name, region → state)

    This is the PRIMARY test that validates the user's reported issue.
    """
    print("\n" + "="*80)
    print("TEST 1: Layer 1 Critical Field Translations")
    print("="*80)

    backend_data = {
        "company_name": "Google",
        "region": "São Paulo",
        "city": "São Paulo",
        "country": "BR",
        "timezone": "America/Sao_Paulo"
    }

    print("\n[BEFORE TRANSLATION]")
    print("Backend data:")
    for key, value in backend_data.items():
        print(f"  {key}: {value}")

    result = translate_fields_for_frontend(backend_data)

    print("\n[AFTER TRANSLATION]")
    print("Frontend data:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    # CRITICAL FIX: User was manually entering company name
    print("\n[VALIDATION]")
    print(f"✅ company_name → name: {'PASS' if 'name' in result and 'company_name' not in result else 'FAIL'}")
    assert result["name"] == "Google"
    assert "company_name" not in result

    # CRITICAL FIX: User was manually entering state
    print(f"✅ region → state: {'PASS' if 'state' in result and 'region' not in result else 'FAIL'}")
    assert result["state"] == "São Paulo"
    assert "region" not in result

    # These should pass through unchanged
    assert result["city"] == "São Paulo"
    assert result["country"] == "BR"
    assert result["timezone"] == "America/Sao_Paulo"

    print("\n✅ ALL CRITICAL TRANSLATIONS PASSED")


def test_ai_prefix_removal():
    """TEST: AI field prefix removal (ai_industry → industry)"""
    print("\n" + "="*80)
    print("TEST 2: AI Field Prefix Removal")
    print("="*80)

    backend_data = {
        "ai_industry": "Technology",
        "ai_company_size": "10001+",
        "ai_digital_maturity": "Advanced",
        "ai_target_audience": "Businesses",
        "ai_key_differentiators": "Innovation"
    }

    print("\n[BEFORE TRANSLATION]")
    for key in backend_data:
        print(f"  {key}")

    result = translate_fields_for_frontend(backend_data)

    print("\n[AFTER TRANSLATION]")
    for key in result:
        print(f"  {key}")

    # All ai_ prefixes should be removed
    print("\n[VALIDATION]")
    assert result["industry"] == "Technology"
    print("✅ ai_industry → industry")

    assert result["companySize"] == "10001+"
    print("✅ ai_company_size → companySize")

    assert result["digitalMaturity"] == "Advanced"
    print("✅ ai_digital_maturity → digitalMaturity")

    assert result["targetAudience"] == "Businesses"
    print("✅ ai_target_audience → targetAudience")

    assert result["keyDifferentiators"] == "Innovation"
    print("✅ ai_key_differentiators → keyDifferentiators")

    # No ai_ prefixed keys should remain
    assert not any(key.startswith("ai_") for key in result.keys())
    print("\n✅ NO AI_ PREFIXES REMAINING")


def test_snake_to_camel_case():
    """TEST: snake_case to camelCase conversion"""
    print("\n" + "="*80)
    print("TEST 3: Snake Case to Camel Case Conversion")
    print("="*80)

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

    print("\n[VALIDATION]")
    assert result["employeeCount"] == "25-50"
    print("✅ employee_count → employeeCount")

    assert result["annualRevenue"] == "$10M-$50M"
    print("✅ annual_revenue → annualRevenue")

    assert result["legalName"] == "Google LLC"
    print("✅ legal_name → legalName")

    assert result["foundedYear"] == 1998
    print("✅ founded_year → foundedYear")

    assert result["websiteTech"] == ["React", "Next.js"]
    print("✅ website_tech → websiteTech")

    assert result["metaDescription"] == "Search engine"
    print("✅ meta_description → metaDescription")

    assert result["logoUrl"] == "https://example.com/logo.png"
    print("✅ logo_url → logoUrl")

    assert result["placeId"] == "ChIJ123ABC"
    print("✅ place_id → placeId")

    print("\n✅ ALL CAMEL CASE CONVERSIONS PASSED")


def test_complete_layer3_response():
    """TEST: Complete Layer 3 data translation (AI + all layers)"""
    print("\n" + "="*80)
    print("TEST 4: Complete Layer 3 Response (ALL LAYERS)")
    print("="*80)

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

    print("\n[BACKEND FIELDS]")
    for key in layer3_backend:
        print(f"  {key}")

    result = translate_fields_for_frontend(layer3_backend)

    print("\n[FRONTEND FIELDS]")
    for key in result:
        print(f"  {key}")

    print("\n[VALIDATION]")

    # All translations should be applied
    assert result["name"] == "TechStart"
    print("✅ company_name → name")

    assert result["state"] == "São Paulo"
    print("✅ region → state")

    assert result["city"] == "São Paulo"
    print("✅ city (pass-through)")

    assert result["employeeCount"] == "25-50"
    print("✅ employee_count → employeeCount")

    assert result["annualRevenue"] == "$1M-$10M"
    print("✅ annual_revenue → annualRevenue")

    assert result["legalName"] == "TechStart Innovations LTDA"
    print("✅ legal_name → legalName")

    assert result["industry"] == "Technology / SaaS"
    print("✅ ai_industry → industry")

    assert result["companySize"] == "25-50"
    print("✅ ai_company_size → companySize")

    assert result["digitalMaturity"] == "Advanced"
    print("✅ ai_digital_maturity → digitalMaturity")

    assert result["targetAudience"] == "B2B Startups"
    print("✅ ai_target_audience → targetAudience")

    assert result["keyDifferentiators"] == "Automation & AI"
    print("✅ ai_key_differentiators → keyDifferentiators")

    # No backend field names should remain
    assert "company_name" not in result
    assert "region" not in result
    assert "employee_count" not in result
    assert not any(key.startswith("ai_") for key in result.keys())

    print("\n✅ ALL BACKEND FIELD NAMES REMOVED")
    print("✅ COMPLETE LAYER 3 TRANSLATION PASSED")


def test_form_field_mapping():
    """
    TEST: CRITICAL - Form field auto-fill mapping

    This validates the EXACT issue: Backend fields must match frontend form fields
    """
    print("\n" + "="*80)
    print("TEST 5: FORM FIELD AUTO-FILL MAPPING (CRITICAL)")
    print("="*80)

    # Backend enrichment data
    backend_data = {
        "company_name": "Google Inc",
        "region": "California",
        "city": "Mountain View",
        "employee_count": "10001+",
        "ai_industry": "Technology"
    }

    print("\n[BACKEND DATA]")
    for key, value in backend_data.items():
        print(f"  {key}: {value}")

    # Apply translation (what backend does before sending to frontend)
    frontend_data = translate_fields_for_frontend(backend_data)

    print("\n[FRONTEND DATA (TRANSLATED)]")
    for key, value in frontend_data.items():
        print(f"  {key}: {value}")

    # Frontend form fields (what the form expects)
    expected_form_fields = {
        "name": "Google Inc",           # ← Should match
        "state": "California",          # ← Should match
        "city": "Mountain View",        # ← Should match
        "employeeCount": "10001+",      # ← Should match
        "industry": "Technology"        # ← Should match
    }

    print("\n[FRONTEND FORM EXPECTS]")
    for field in expected_form_fields:
        print(f"  {field}")

    print("\n[VALIDATION]")

    # Validate EVERY field matches
    all_match = True
    for form_field, expected_value in expected_form_fields.items():
        if form_field in frontend_data:
            actual_value = frontend_data[form_field]
            if actual_value == expected_value:
                print(f"✅ {form_field}: {actual_value} (MATCH)")
            else:
                print(f"❌ {form_field}: {actual_value} != {expected_value} (VALUE MISMATCH)")
                all_match = False
        else:
            print(f"❌ {form_field}: MISSING")
            all_match = False
            available_fields = list(frontend_data.keys())
            print(f"   Available fields: {available_fields}")

    assert all_match, "Not all form fields matched!"

    print("\n✅ ALL FRONTEND FORM FIELDS MATCH TRANSLATED BACKEND DATA!")


def run_all_tests():
    """Run all standalone tests"""
    print("\n" + "="*80)
    print("PROGRESSIVE ENRICHMENT - FIELD TRANSLATION E2E TESTS")
    print("="*80)

    tests = [
        test_critical_layer1_translations,
        test_ai_prefix_removal,
        test_snake_to_camel_case,
        test_complete_layer3_response,
        test_form_field_mapping
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"\n❌ TEST FAILED: {test_func.__name__}")
            print(f"   Error: {e}")
        except Exception as e:
            failed += 1
            print(f"\n❌ TEST ERROR: {test_func.__name__}")
            print(f"   Error: {e}")

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"✅ Passed: {passed}/{len(tests)}")
    if failed > 0:
        print(f"❌ Failed: {failed}/{len(tests)}")
    else:
        print("🎉 ALL TESTS PASSED!")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
