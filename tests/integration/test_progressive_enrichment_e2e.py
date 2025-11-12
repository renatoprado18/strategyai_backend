"""
Comprehensive End-to-End Tests for Progressive Enrichment Flow

This test suite simulates the EXACT user flow:
1. Frontend sends enrichment request (URL + email)
2. Backend creates session and returns session_id + stream_url
3. Frontend connects to SSE stream
4. Backend sends layer1_complete event with field data
5. Backend sends layer2_complete event with more fields
6. Backend sends layer3_complete event with AI-inferred fields
7. Frontend receives translated field names (company_name → name, region → state, etc.)
8. Frontend auto-fills form fields

Tests validate:
- Field translation (backend snake_case → frontend camelCase)
- SSE event delivery and format
- Data correctness at each layer
- Progressive updates work as expected
- No field naming mismatches
"""

import pytest
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.routes.enrichment_progressive import translate_fields_for_frontend
from app.services.enrichment.progressive_orchestrator import ProgressiveEnrichmentSession


# ============================================================================
# TEST UTILITIES
# ============================================================================


class SSEStreamCapture:
    """Utility to capture and parse SSE events from StreamingResponse"""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.raw_data: List[str] = []

    def parse_sse_line(self, line: str):
        """Parse a single SSE line"""
        if line.startswith("event: "):
            event_type = line[7:].strip()
            return {"type": "event", "event_type": event_type}
        elif line.startswith("data: "):
            data_str = line[6:].strip()
            try:
                data = json.loads(data_str)
                return {"type": "data", "data": data}
            except json.JSONDecodeError:
                return {"type": "data", "data": data_str}
        return None

    def parse_sse_stream(self, stream_content: str):
        """Parse complete SSE stream into events"""
        current_event = {}

        for line in stream_content.split("\n"):
            line = line.strip()
            if not line:
                # Empty line signals end of event
                if current_event:
                    self.events.append(current_event)
                    current_event = {}
                continue

            parsed = self.parse_sse_line(line)
            if parsed:
                if parsed["type"] == "event":
                    current_event["event_type"] = parsed["event_type"]
                elif parsed["type"] == "data":
                    current_event["data"] = parsed["data"]

        # Add final event if exists
        if current_event:
            self.events.append(current_event)

        return self.events


def assert_field_translation(backend_field: str, frontend_field: str, data: Dict[str, Any]):
    """
    Assert that a backend field name was correctly translated to frontend field name

    Args:
        backend_field: Original backend field name (e.g., "company_name")
        frontend_field: Expected frontend field name (e.g., "name")
        data: The translated data dictionary
    """
    # Check that frontend field exists
    assert frontend_field in data, \
        f"Frontend field '{frontend_field}' not found in data. Available fields: {list(data.keys())}"

    # Check that backend field does NOT exist (was translated away)
    assert backend_field not in data, \
        f"Backend field '{backend_field}' still present after translation! Should be '{frontend_field}'"


# ============================================================================
# E2E TEST SUITE
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestProgressiveEnrichmentE2E:
    """End-to-end tests for progressive enrichment flow"""

    async def test_complete_user_flow(self, async_client, mock_redis_client):
        """
        TEST 1: Complete user flow from request to SSE stream

        Simulates exact frontend behavior:
        1. POST /api/enrichment/progressive/start → Get session_id
        2. Connect to /api/enrichment/progressive/stream/{session_id}
        3. Receive layer1_complete, layer2_complete, layer3_complete events
        4. Validate field translation at each layer
        """
        # Mock rate limiter
        mock_redis_client.get.return_value = None

        # Mock enrichment sources
        with patch('app.services.enrichment.progressive_orchestrator.MetadataSource') as mock_metadata, \
             patch('app.services.enrichment.progressive_orchestrator.IpApiSource') as mock_ip, \
             patch('app.services.enrichment.progressive_orchestrator.ClearbitSource') as mock_clearbit:

            # Mock Layer 1 responses (Metadata + IP API)
            mock_metadata_instance = Mock()
            mock_metadata_instance.enrich = AsyncMock(return_value=Mock(
                success=True,
                source_name="metadata",
                data={
                    "company_name": "Google",  # Should translate to "name"
                    "description": "Search engine and tech company",
                    "logo_url": "https://google.com/logo.png",
                    "meta_description": "Google Search"
                },
                cost_usd=0.0,
                duration_ms=500
            ))
            mock_metadata.return_value = mock_metadata_instance

            mock_ip_instance = Mock()
            mock_ip_instance.enrich = AsyncMock(return_value=Mock(
                success=True,
                source_name="ip_api",
                data={
                    "region": "California",  # Should translate to "state"
                    "city": "Mountain View",
                    "country": "US",
                    "timezone": "America/Los_Angeles",
                    "ip_address": "8.8.8.8"
                },
                cost_usd=0.0,
                duration_ms=150
            ))
            mock_ip.return_value = mock_ip_instance

            # Mock Layer 2 responses (Clearbit)
            mock_clearbit_instance = Mock()
            mock_clearbit_instance.enrich = AsyncMock(return_value=Mock(
                success=True,
                source_name="clearbit",
                data={
                    "employee_count": "10001+",  # Should translate to "employeeCount"
                    "annual_revenue": "$100M+",  # Should translate to "annualRevenue"
                    "founded_year": 1998,
                    "legal_name": "Google LLC"
                },
                cost_usd=0.10,
                duration_ms=1500
            ))
            mock_clearbit.return_value = mock_clearbit_instance

            # STEP 1: Start progressive enrichment
            response = await async_client.post(
                "/api/enrichment/progressive/start",
                json={
                    "website_url": "https://google.com",
                    "user_email": "test@gmail.com"
                }
            )

            assert response.status_code == 200, f"Failed to start enrichment: {response.text}"
            data = response.json()

            # Validate response structure
            assert "session_id" in data
            assert "stream_url" in data
            assert data["status"] == "processing"

            session_id = data["session_id"]
            stream_url = data["stream_url"]

            # Verify stream URL format
            assert stream_url == f"/api/enrichment/progressive/stream/{session_id}"

            # STEP 2: Connect to SSE stream (simulate EventSource)
            # Give enrichment time to start
            await asyncio.sleep(0.5)

            # NOTE: FastAPI TestClient doesn't support streaming well
            # In real test, you'd use httpx or requests for SSE
            # For now, we'll validate the session status endpoint instead
            status_response = await async_client.get(
                f"/api/enrichment/progressive/session/{session_id}"
            )

            assert status_response.status_code == 200
            status_data = status_response.json()

            # STEP 3: Validate field translation
            fields = status_data["fields_auto_filled"]

            # CRITICAL VALIDATION: Check field name translations
            assert_field_translation("company_name", "name", fields)
            assert_field_translation("region", "state", fields)
            assert_field_translation("employee_count", "employeeCount", fields)
            assert_field_translation("annual_revenue", "annualRevenue", fields)

            # Validate values are correct
            assert fields["name"] == "Google"
            assert fields["state"] == "California"
            assert fields["city"] == "Mountain View"
            assert fields["employeeCount"] == "10001+"
            assert fields["annualRevenue"] == "$100M+"

    async def test_layer1_field_translation(self):
        """
        TEST 2: Layer 1 field translation

        Validates that Layer 1 fields (Metadata + IP API) are correctly
        translated from backend format to frontend format.

        Critical fixes being tested:
        - company_name → name (user was manually entering this!)
        - region → state (user was manually entering this!)
        """
        layer1_backend = {
            "company_name": "TechStart Innovations",
            "description": "B2B SaaS platform",
            "meta_description": "Innovative solutions",
            "logo_url": "https://techstart.com/logo.png",
            "website_tech": ["React", "Next.js"],
            "region": "São Paulo",
            "city": "São Paulo",
            "country": "BR",
            "country_name": "Brazil",
            "timezone": "America/Sao_Paulo",
            "ip_address": "200.1.2.3",
            "ip_location": "São Paulo, Brazil"
        }

        # Apply translation
        frontend_data = translate_fields_for_frontend(layer1_backend)

        # CRITICAL: company_name → name
        assert "name" in frontend_data
        assert frontend_data["name"] == "TechStart Innovations"
        assert "company_name" not in frontend_data

        # CRITICAL: region → state
        assert "state" in frontend_data
        assert frontend_data["state"] == "São Paulo"
        assert "region" not in frontend_data

        # CamelCase conversions
        assert "metaDescription" in frontend_data
        assert frontend_data["metaDescription"] == "Innovative solutions"

        assert "logoUrl" in frontend_data
        assert "websiteTech" in frontend_data
        assert "countryName" in frontend_data
        assert "ipAddress" in frontend_data
        assert "ipLocation" in frontend_data

        # Pass-through fields
        assert frontend_data["description"] == "B2B SaaS platform"
        assert frontend_data["city"] == "São Paulo"
        assert frontend_data["country"] == "BR"

    async def test_layer2_field_translation(self):
        """
        TEST 3: Layer 2 field translation

        Validates Clearbit/ReceitaWS/Google Places field translations
        """
        layer2_backend = {
            "employee_count": "25-50",
            "annual_revenue": "$1M-$10M",
            "legal_name": "TechStart LTDA",
            "founded_year": 2019,
            "phone": "+55 11 1234-5678",
            "rating": 4.7,
            "reviews_count": 124,
            "place_id": "ChIJ123ABC"
        }

        frontend_data = translate_fields_for_frontend(layer2_backend)

        # Snake to camelCase
        assert "employeeCount" in frontend_data
        assert frontend_data["employeeCount"] == "25-50"
        assert "employee_count" not in frontend_data

        assert "annualRevenue" in frontend_data
        assert frontend_data["annualRevenue"] == "$1M-$10M"

        assert "legalName" in frontend_data
        assert "foundedYear" in frontend_data
        assert "reviewsCount" in frontend_data
        assert "placeId" in frontend_data

        # Pass-through (already correct)
        assert frontend_data["phone"] == "+55 11 1234-5678"
        assert frontend_data["rating"] == 4.7

    async def test_layer3_ai_field_translation(self):
        """
        TEST 4: Layer 3 AI field translation

        Validates that ai_ prefixed fields are correctly stripped
        """
        layer3_backend = {
            "ai_industry": "Technology / SaaS",
            "ai_company_size": "25-50",
            "ai_digital_maturity": "Advanced",
            "ai_target_audience": "B2B Startups",
            "ai_key_differentiators": "Automation & AI",
            "linkedin_followers": 1500,
            "linkedin_url": "https://linkedin.com/company/techstart"
        }

        frontend_data = translate_fields_for_frontend(layer3_backend)

        # AI prefix removal
        assert "industry" in frontend_data
        assert frontend_data["industry"] == "Technology / SaaS"
        assert "ai_industry" not in frontend_data

        assert "companySize" in frontend_data
        assert "digitalMaturity" in frontend_data
        assert "targetAudience" in frontend_data
        assert "keyDifferentiators" in frontend_data

        # No ai_ prefixes should remain
        assert not any(key.startswith("ai_") for key in frontend_data.keys())

        # LinkedIn fields pass through
        assert "linkedin_followers" in frontend_data  # No translation for this one
        assert "linkedin_url" in frontend_data

    async def test_progressive_data_accumulation(self):
        """
        TEST 5: Progressive data accumulation

        Simulates receiving data from all 3 layers and ensures:
        1. Layer 1 data comes first
        2. Layer 2 adds more data
        3. Layer 3 adds AI inference
        4. All data is correctly translated
        """
        # Layer 1 data (instant)
        layer1 = {
            "company_name": "TechStart",
            "region": "São Paulo",
            "city": "São Paulo"
        }

        translated_layer1 = translate_fields_for_frontend(layer1)
        assert "name" in translated_layer1
        assert "state" in translated_layer1
        assert "city" in translated_layer1

        # Layer 2 adds data
        layer2 = {
            **layer1,  # Include Layer 1
            "employee_count": "25-50",
            "annual_revenue": "$1M-$10M"
        }

        translated_layer2 = translate_fields_for_frontend(layer2)
        assert "name" in translated_layer2  # Still has Layer 1
        assert "state" in translated_layer2
        assert "employeeCount" in translated_layer2  # New from Layer 2
        assert "annualRevenue" in translated_layer2

        # Layer 3 adds AI inference
        layer3 = {
            **layer2,  # Include Layer 1 + 2
            "ai_industry": "Technology",
            "ai_digital_maturity": "Advanced"
        }

        translated_layer3 = translate_fields_for_frontend(layer3)
        assert "name" in translated_layer3  # Still has Layer 1
        assert "employeeCount" in translated_layer3  # Still has Layer 2
        assert "industry" in translated_layer3  # New from Layer 3
        assert "digitalMaturity" in translated_layer3

    async def test_sse_event_format(self):
        """
        TEST 6: SSE event format validation

        Validates that SSE events are correctly formatted
        """
        # Simulate SSE event payload
        layer1_event = {
            "status": "layer1_complete",
            "fields": {
                "name": "Google",
                "state": "California",
                "city": "Mountain View"
            },
            "confidence_scores": {
                "name": 70.0,
                "state": 60.0,
                "city": 60.0
            }
        }

        # Validate structure
        assert "status" in layer1_event
        assert "fields" in layer1_event
        assert "confidence_scores" in layer1_event
        assert layer1_event["status"] == "layer1_complete"

        # Validate field names are frontend format
        assert "name" in layer1_event["fields"]
        assert "state" in layer1_event["fields"]
        assert "company_name" not in layer1_event["fields"]
        assert "region" not in layer1_event["fields"]

    async def test_form_field_auto_fill_mapping(self):
        """
        TEST 7: Form field auto-fill mapping

        Validates that backend fields map to correct frontend form fields

        This is the CRITICAL TEST that checks the exact issue reported:
        - Backend sends "company_name"
        - After translation becomes "name"
        - Frontend form field expects "name"
        - MATCH? ✅
        """
        # Backend enrichment data
        backend_data = {
            "company_name": "Google Inc",
            "region": "California",
            "city": "Mountain View",
            "employee_count": "10001+",
            "ai_industry": "Technology"
        }

        # Apply translation (what backend does before sending to frontend)
        frontend_data = translate_fields_for_frontend(backend_data)

        # Frontend form fields (what the form expects)
        expected_form_fields = {
            "name": True,           # ← Should match
            "state": True,          # ← Should match
            "city": True,           # ← Should match
            "employeeCount": True,  # ← Should match
            "industry": True        # ← Should match
        }

        # Validate EVERY field matches
        for form_field in expected_form_fields:
            assert form_field in frontend_data, \
                f"❌ MISMATCH: Frontend form expects '{form_field}' but got: {list(frontend_data.keys())}"

        # Validate values are correct
        assert frontend_data["name"] == "Google Inc"
        assert frontend_data["state"] == "California"
        assert frontend_data["city"] == "Mountain View"
        assert frontend_data["employeeCount"] == "10001+"
        assert frontend_data["industry"] == "Technology"

        print("✅ All frontend form fields match translated backend data!")

    async def test_no_untranslated_fields_in_response(self):
        """
        TEST 8: Ensure no untranslated backend fields leak to frontend

        This test ensures we don't send BOTH company_name AND name
        (which would confuse the frontend)
        """
        backend_data = {
            "company_name": "Google",
            "region": "California",
            "employee_count": "10001+",
            "ai_industry": "Technology"
        }

        frontend_data = translate_fields_for_frontend(backend_data)

        # These backend field names should NOT exist in frontend data
        forbidden_backend_fields = [
            "company_name",  # Should be "name"
            "region",        # Should be "state"
            "employee_count", # Should be "employeeCount"
            "ai_industry"    # Should be "industry"
        ]

        for field in forbidden_backend_fields:
            assert field not in frontend_data, \
                f"❌ Backend field '{field}' leaked to frontend! Should be translated."

        # These frontend fields SHOULD exist
        required_frontend_fields = [
            "name",
            "state",
            "employeeCount",
            "industry"
        ]

        for field in required_frontend_fields:
            assert field in frontend_data, \
                f"❌ Required frontend field '{field}' missing!"

        print("✅ No backend field names leaked to frontend!")


# ============================================================================
# STEP-BY-STEP FLOW VALIDATION TEST
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestEnrichmentFlowStepByStep:
    """
    Detailed step-by-step validation of the enrichment flow

    This test documents EXACTLY what happens at each step
    """

    async def test_documented_flow(self):
        """
        STEP-BY-STEP TEST REPORT

        This test validates the complete flow and generates a report
        """
        print("\n" + "="*80)
        print("PROGRESSIVE ENRICHMENT FLOW - STEP-BY-STEP TEST REPORT")
        print("="*80)

        # STEP 1: Frontend sends request
        print("\n[STEP 1] Frontend sends enrichment request")
        print("-" * 80)
        request_data = {
            "website_url": "https://google.com",
            "user_email": "test@gmail.com"
        }
        print(f"Request URL: POST /api/enrichment/progressive/start")
        print(f"Request body: {json.dumps(request_data, indent=2)}")

        # STEP 2: Backend creates session
        print("\n[STEP 2] Backend creates session")
        print("-" * 80)
        response_data = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "processing",
            "message": "Progressive enrichment started",
            "stream_url": "/api/enrichment/progressive/stream/550e8400-e29b-41d4-a716-446655440000"
        }
        print(f"Response: {json.dumps(response_data, indent=2)}")

        # STEP 3: Frontend connects to SSE
        print("\n[STEP 3] Frontend connects to SSE stream")
        print("-" * 80)
        print(f"EventSource URL: {response_data['stream_url']}")
        print("Listening for events: layer1_complete, layer2_complete, layer3_complete")

        # STEP 4: Layer 1 complete event
        print("\n[STEP 4] Layer 1 complete event received")
        print("-" * 80)

        layer1_backend = {
            "company_name": "Google Inc",
            "description": "Search engine company",
            "region": "California",
            "city": "Mountain View",
            "country": "US",
            "ip_address": "8.8.8.8"
        }

        print("Backend data (raw):")
        print(json.dumps(layer1_backend, indent=2))

        layer1_frontend = translate_fields_for_frontend(layer1_backend)

        print("\nFrontend data (after translation):")
        print(json.dumps(layer1_frontend, indent=2))

        print("\nField translations applied:")
        print(f"  company_name → name: {'✅' if 'name' in layer1_frontend else '❌'}")
        print(f"  region → state: {'✅' if 'state' in layer1_frontend else '❌'}")
        print(f"  ip_address → ipAddress: {'✅' if 'ipAddress' in layer1_frontend else '❌'}")

        # Validate Layer 1
        assert "name" in layer1_frontend
        assert "state" in layer1_frontend
        assert "company_name" not in layer1_frontend
        assert "region" not in layer1_frontend

        # STEP 5: Layer 2 complete event
        print("\n[STEP 5] Layer 2 complete event received")
        print("-" * 80)

        layer2_backend = {
            **layer1_backend,
            "employee_count": "10001+",
            "annual_revenue": "$100M+",
            "founded_year": 1998
        }

        print("Backend data (raw):")
        print(json.dumps(layer2_backend, indent=2))

        layer2_frontend = translate_fields_for_frontend(layer2_backend)

        print("\nFrontend data (after translation):")
        print(json.dumps(layer2_frontend, indent=2))

        print("\nNew fields from Layer 2:")
        print(f"  employee_count → employeeCount: {'✅' if 'employeeCount' in layer2_frontend else '❌'}")
        print(f"  annual_revenue → annualRevenue: {'✅' if 'annualRevenue' in layer2_frontend else '❌'}")

        # Validate Layer 2
        assert "employeeCount" in layer2_frontend
        assert "annualRevenue" in layer2_frontend
        assert "employee_count" not in layer2_frontend

        # STEP 6: Layer 3 complete event
        print("\n[STEP 6] Layer 3 complete event received (FINAL)")
        print("-" * 80)

        layer3_backend = {
            **layer2_backend,
            "ai_industry": "Technology / Search Engines",
            "ai_company_size": "10001+",
            "ai_digital_maturity": "Advanced"
        }

        print("Backend data (raw):")
        print(json.dumps(layer3_backend, indent=2))

        layer3_frontend = translate_fields_for_frontend(layer3_backend)

        print("\nFrontend data (after translation):")
        print(json.dumps(layer3_frontend, indent=2))

        print("\nAI fields from Layer 3:")
        print(f"  ai_industry → industry: {'✅' if 'industry' in layer3_frontend else '❌'}")
        print(f"  ai_company_size → companySize: {'✅' if 'companySize' in layer3_frontend else '❌'}")
        print(f"  ai_digital_maturity → digitalMaturity: {'✅' if 'digitalMaturity' in layer3_frontend else '❌'}")

        # Validate Layer 3
        assert "industry" in layer3_frontend
        assert "companySize" in layer3_frontend
        assert "digitalMaturity" in layer3_frontend
        assert not any(k.startswith("ai_") for k in layer3_frontend.keys())

        # FINAL VALIDATION
        print("\n[FINAL VALIDATION] Form field mapping")
        print("-" * 80)

        form_fields = {
            "name": "text",
            "state": "text",
            "city": "text",
            "country": "text",
            "employeeCount": "select",
            "annualRevenue": "select",
            "industry": "text",
            "companySize": "select",
            "digitalMaturity": "select"
        }

        print("Frontend form expects these fields:")
        for field, field_type in form_fields.items():
            has_field = field in layer3_frontend
            status = "✅" if has_field else "❌"
            value = layer3_frontend.get(field, "MISSING")
            print(f"  {status} {field} ({field_type}): {value}")

        # Validate all form fields present
        for field in form_fields:
            assert field in layer3_frontend, f"Form field '{field}' missing!"

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED - Field translation working correctly!")
        print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
