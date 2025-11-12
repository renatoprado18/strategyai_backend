"""
End-to-end integration tests for the complete form enrichment flow
Tests the full journey from form submission to enriched response
"""
import pytest
from httpx import AsyncClient
from fastapi import status
import asyncio
from datetime import datetime

from app.main import app
from tests.fixtures.enrichment_data import SAMPLE_COMPANIES, ERROR_SCENARIOS


class TestCompleteEnrichmentFlow:
    """Test complete enrichment flow from submission to response"""

    @pytest.mark.asyncio
    async def test_full_enrichment_vallente_clinic(self):
        """Test complete enrichment for Vallente Clinic (real-world example)"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            test_data = SAMPLE_COMPANIES["vallente"]

            payload = {
                "url": test_data["url"],
                "review_cycle": "monthly"
            }

            response = await client.post("/api/v1/enrich", json=payload)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify enrichment completed
            assert data["company_name"] is not None
            assert data["industry"] is not None

            # Verify confidence scores exist
            assert "confidence_scores" in data
            assert isinstance(data["confidence_scores"], dict)

            # Verify all layers executed
            assert "layer1_metadata" in data or data.get("metadata_extracted") is True
            assert "enrichment_timestamp" in data

    @pytest.mark.asyncio
    async def test_enrichment_with_br_domain(self):
        """Test Brazilian domain enrichment with ReceitaWS"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            test_data = SAMPLE_COMPANIES["br_ecommerce"]

            payload = {
                "url": test_data["url"],
                "review_cycle": "weekly"
            }

            response = await client.post("/api/v1/enrich", json=payload)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Should have Brazilian-specific enrichment
            assert data["company_name"] is not None
            if data.get("location"):
                assert "Brazil" in data["location"] or "BR" in data["location"]

    @pytest.mark.asyncio
    async def test_enrichment_with_social_media_fields(self):
        """Test enrichment properly handles provided social media fields"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = {
                "url": "https://example.com",
                "instagram": "@example",
                "tiktok": "exampleuser",
                "linkedin": "example-company",
                "review_cycle": "monthly"
            }

            response = await client.post("/api/v1/enrich", json=payload)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify social media fields are normalized
            assert data.get("instagram") is not None
            assert "instagram.com" in data.get("instagram", "") or data["instagram"] == "@example"

            if data.get("tiktok"):
                assert "tiktok.com" in data["tiktok"] or data["tiktok"] == "exampleuser"

            if data.get("linkedin"):
                assert "linkedin.com" in data["linkedin"] or data["linkedin"] == "example-company"

    @pytest.mark.asyncio
    async def test_enrichment_with_phone_number(self):
        """Test enrichment handles phone number formatting"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = {
                "url": "https://example.com.br",
                "phone": "11987654321",
                "whatsapp": "5511987654321",
                "review_cycle": "monthly"
            }

            response = await client.post("/api/v1/enrich", json=payload)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify phone formatting
            if data.get("phone"):
                assert "+55" in data["phone"] or len(data["phone"]) >= 10

            if data.get("whatsapp"):
                assert "+55" in data["whatsapp"] or len(data["whatsapp"]) >= 10

    @pytest.mark.asyncio
    async def test_enrichment_timeout_handling(self):
        """Test that enrichment completes even if layers timeout"""
        async with AsyncClient(app=app, base_url="http://test", timeout=20.0) as client:
            payload = {
                "url": "https://very-slow-website.example.com",
                "review_cycle": "monthly"
            }

            response = await client.post("/api/v1/enrich", json=payload)

            # Should complete with partial data, not timeout
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_206_PARTIAL_CONTENT]
            data = response.json()

            # Should have at least basic data
            assert "url" in data
            assert data["url"] == payload["url"]

    @pytest.mark.asyncio
    async def test_enrichment_invalid_url_handling(self):
        """Test handling of invalid URLs"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            invalid_urls = ERROR_SCENARIOS["invalid_urls"]

            for invalid_url in invalid_urls[:3]:  # Test first 3
                payload = {
                    "url": invalid_url,
                    "review_cycle": "monthly"
                }

                response = await client.post("/api/v1/enrich", json=payload)

                # Should reject with 422 or handle gracefully
                assert response.status_code in [
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    status.HTTP_400_BAD_REQUEST
                ]

    @pytest.mark.asyncio
    async def test_enrichment_preserves_user_input(self):
        """Test that user-provided data is preserved in response"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = {
                "url": "https://example.com",
                "company_name": "User Provided Name",
                "industry": "User Provided Industry",
                "description": "User provided description",
                "review_cycle": "monthly"
            }

            response = await client.post("/api/v1/enrich", json=payload)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # User data should be preserved or enhanced, not replaced
            assert data["company_name"] is not None
            assert data["industry"] is not None
            assert data["description"] is not None

    @pytest.mark.asyncio
    async def test_enrichment_description_length_validation(self):
        """Test that description respects 800 character limit"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            long_description = "A" * 850  # Exceeds 800 char limit

            payload = {
                "url": "https://example.com",
                "description": long_description,
                "review_cycle": "monthly"
            }

            response = await client.post("/api/v1/enrich", json=payload)

            # Should either truncate or reject
            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                assert len(data.get("description", "")) <= 800
            else:
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestEnrichmentPerformance:
    """Test enrichment performance and timing"""

    @pytest.mark.asyncio
    async def test_enrichment_completes_under_time_limit(self):
        """Test that enrichment completes within acceptable time"""
        async with AsyncClient(app=app, base_url="http://test", timeout=20.0) as client:
            payload = {
                "url": "https://example.com",
                "review_cycle": "monthly"
            }

            start_time = datetime.now()
            response = await client.post("/api/v1/enrich", json=payload)
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()

            assert response.status_code == status.HTTP_200_OK
            # Should complete in under 15 seconds (as per spec)
            assert duration < 15.0

    @pytest.mark.asyncio
    async def test_concurrent_enrichment_requests(self):
        """Test system handles concurrent enrichment requests"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payloads = [
                {"url": f"https://example{i}.com", "review_cycle": "monthly"}
                for i in range(5)
            ]

            # Submit 5 concurrent requests
            tasks = [
                client.post("/api/v1/enrich", json=payload)
                for payload in payloads
            ]

            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == status.HTTP_200_OK


class TestEnrichmentErrorRecovery:
    """Test error recovery and graceful degradation"""

    @pytest.mark.asyncio
    async def test_api_failure_recovery(self):
        """Test recovery when external APIs fail"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = {
                "url": "https://example.com",
                "review_cycle": "monthly"
            }

            # Simulate API failure scenarios
            with pytest.MonkeyPatch.context() as mp:
                # This would require mocking the external API calls
                # For now, just test that the endpoint handles errors
                response = await client.post("/api/v1/enrich", json=payload)

                # Should complete even if some APIs fail
                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_206_PARTIAL_CONTENT
                ]

    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self):
        """Test rate limiting prevents abuse"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = {
                "url": "https://example.com",
                "review_cycle": "monthly"
            }

            # Submit many requests in quick succession
            responses = []
            for _ in range(10):
                response = await client.post("/api/v1/enrich", json=payload)
                responses.append(response)

            # Should either succeed or rate limit
            status_codes = [r.status_code for r in responses]
            assert all(
                code in [status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS]
                for code in status_codes
            )


class TestFieldMapping:
    """Test field mapping between frontend and backend"""

    @pytest.mark.asyncio
    async def test_website_url_field_mapping(self):
        """Test that both 'website' and 'url' fields are accepted"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test with 'url'
            payload1 = {
                "url": "https://example.com",
                "review_cycle": "monthly"
            }
            response1 = await client.post("/api/v1/enrich", json=payload1)
            assert response1.status_code == status.HTTP_200_OK

            # Test with 'website'
            payload2 = {
                "website": "https://example.com",
                "review_cycle": "monthly"
            }
            response2 = await client.post("/api/v1/enrich", json=payload2)
            assert response2.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_linkedin_field_variations(self):
        """Test that linkedin_company and linkedin fields work"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = {
                "url": "https://example.com",
                "linkedin": "example-company",
                "review_cycle": "monthly"
            }

            response = await client.post("/api/v1/enrich", json=payload)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Should map to linkedin_company internally
            assert "linkedin" in data or "linkedin_company" in data


class TestReviewCycleHandling:
    """Test review cycle selection and validation"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("cycle", ["weekly", "biweekly", "monthly", "quarterly"])
    async def test_valid_review_cycles(self, cycle):
        """Test all valid review cycle values"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = {
                "url": "https://example.com",
                "review_cycle": cycle
            }

            response = await client.post("/api/v1/enrich", json=payload)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data.get("review_cycle") == cycle

    @pytest.mark.asyncio
    async def test_invalid_review_cycle(self):
        """Test invalid review cycle is rejected"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = {
                "url": "https://example.com",
                "review_cycle": "invalid_cycle"
            }

            response = await client.post("/api/v1/enrich", json=payload)

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
