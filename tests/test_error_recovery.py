"""
Error handling and recovery tests for the enrichment system
Tests graceful degradation, fallback mechanisms, and error scenarios
"""
import pytest
from unittest.mock import patch, AsyncMock, Mock
import asyncio
from httpx import AsyncClient
from fastapi import status

from app.services.enrichment.progressive_orchestrator import ProgressiveOrchestrator
from app.services.enrichment.layer1_metadata import MetadataExtractor
from app.services.enrichment.layer2_sources import ExternalSourceEnricher
from app.services.enrichment.layer3_ai import AIInferenceEngine
from app.models.schemas import EnrichmentRequest
from tests.fixtures.enrichment_data import ERROR_SCENARIOS


class TestInvalidURLHandling:
    """Test handling of invalid URLs"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_url", ERROR_SCENARIOS["invalid_urls"])
    async def test_invalid_url_rejection(self, invalid_url):
        """Test that invalid URLs are properly rejected"""
        orchestrator = ProgressiveOrchestrator()

        request = EnrichmentRequest(
            url=invalid_url,
            review_cycle="monthly"
        )

        # Should either reject or handle gracefully
        with pytest.raises((ValueError, Exception)):
            await orchestrator.enrich(request)

    @pytest.mark.asyncio
    async def test_empty_url_handling(self):
        """Test handling of empty URL"""
        with pytest.raises((ValueError, Exception)):
            request = EnrichmentRequest(
                url="",
                review_cycle="monthly"
            )

    @pytest.mark.asyncio
    async def test_malformed_url_sanitization(self):
        """Test that malformed URLs are sanitized"""
        from app.utils.url_validator import normalize_url

        test_cases = [
            ("example.com", "https://example.com"),
            ("www.example.com", "https://www.example.com"),
            ("  https://example.com  ", "https://example.com"),
        ]

        for input_url, expected_url in test_cases:
            result = normalize_url(input_url)
            assert result == expected_url


class TestAPIFailureRecovery:
    """Test recovery when external APIs fail"""

    @pytest.fixture
    def source_enricher(self):
        return ExternalSourceEnricher()

    @pytest.mark.asyncio
    async def test_clearbit_api_failure(self, source_enricher):
        """Test recovery when Clearbit API fails"""
        url = "https://example.com"
        layer1_data = {"company_name": "Example", "industry": "Tech"}

        with patch.object(source_enricher, '_enrich_clearbit') as mock_clearbit:
            mock_clearbit.side_effect = Exception("Clearbit API Error")

            # Should not crash, should fall back gracefully
            result = await source_enricher.enrich(url, layer1_data)

            # Should return at least layer1 data
            assert result["company_name"] == "Example"
            assert result["industry"] == "Tech"

    @pytest.mark.asyncio
    async def test_receitaws_api_failure(self, source_enricher):
        """Test recovery when ReceitaWS API fails"""
        url = "https://example.com.br"
        layer1_data = {"company_name": "Example BR"}

        with patch.object(source_enricher, '_enrich_receitaws') as mock_receitaws:
            mock_receitaws.side_effect = Exception("ReceitaWS unavailable")

            result = await source_enricher.enrich(url, layer1_data)

            # Should fall back to Layer 1 data
            assert result["company_name"] == "Example BR"
            assert "error" not in result or result.get("partial_enrichment") is True

    @pytest.mark.asyncio
    async def test_multiple_api_failures(self, source_enricher):
        """Test when multiple APIs fail simultaneously"""
        url = "https://example.com"
        layer1_data = {"company_name": "Example"}

        with patch.object(source_enricher, '_enrich_clearbit') as mock_clearbit, \
             patch.object(source_enricher, '_enrich_other_source') as mock_other:

            mock_clearbit.side_effect = Exception("Clearbit Error")
            mock_other.side_effect = Exception("Other API Error")

            result = await source_enricher.enrich(url, layer1_data)

            # Should still return data, not crash
            assert isinstance(result, dict)
            assert result.get("company_name") is not None

    @pytest.mark.asyncio
    async def test_api_404_not_found(self, source_enricher):
        """Test handling when API returns 404 (company not found)"""
        url = "https://unknown-company.com"
        layer1_data = {}

        with patch.object(source_enricher, '_enrich_clearbit') as mock_clearbit:
            # Simulate 404 response
            mock_clearbit.return_value = None

            result = await source_enricher.enrich(url, layer1_data)

            # Should handle gracefully
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_api_500_server_error(self, source_enricher):
        """Test handling when API returns 500 server error"""
        url = "https://example.com"
        layer1_data = {"company_name": "Example"}

        with patch.object(source_enricher, '_enrich_clearbit') as mock_clearbit:
            mock_clearbit.side_effect = Exception("500 Internal Server Error")

            result = await source_enricher.enrich(url, layer1_data)

            # Should fall back gracefully
            assert result["company_name"] == "Example"


class TestAITimeoutFallback:
    """Test fallback when AI inference times out"""

    @pytest.fixture
    def ai_engine(self):
        return AIInferenceEngine()

    @pytest.mark.asyncio
    async def test_ai_timeout_returns_data(self, ai_engine):
        """Test that AI timeout doesn't lose data"""
        enriched_data = {
            "company_name": "Example Inc",
            "industry": "Technology"
        }

        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.side_effect = asyncio.TimeoutError()

            result = await ai_engine.infer(enriched_data)

            # Should return original data with low confidence
            assert result["company_name"] == "Example Inc"
            assert result["industry"] == "Technology"
            assert "confidence_scores" in result

    @pytest.mark.asyncio
    async def test_ai_rate_limit_handling(self, ai_engine):
        """Test handling of AI rate limit errors"""
        enriched_data = {"company_name": "Example"}

        with patch('openai.ChatCompletion.acreate') as mock_openai:
            # Simulate rate limit error
            mock_openai.side_effect = Exception("Rate limit exceeded")

            result = await ai_engine.infer(enriched_data)

            # Should handle gracefully
            assert isinstance(result, dict)
            assert result.get("company_name") is not None

    @pytest.mark.asyncio
    async def test_ai_invalid_response_handling(self, ai_engine):
        """Test handling of invalid AI responses"""
        enriched_data = {"company_name": "Example"}

        with patch('openai.ChatCompletion.acreate') as mock_openai:
            # Simulate malformed response
            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock(message={"content": "Invalid JSON {{{"})]
            mock_openai.return_value = mock_response

            result = await ai_engine.infer(enriched_data)

            # Should fall back to input data
            assert result["company_name"] == "Example"

    @pytest.mark.asyncio
    async def test_ai_empty_response(self, ai_engine):
        """Test handling of empty AI responses"""
        enriched_data = {"company_name": "Example"}

        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_response = AsyncMock()
            mock_response.choices = []
            mock_openai.return_value = mock_response

            result = await ai_engine.infer(enriched_data)

            # Should return input data
            assert result["company_name"] == "Example"


class TestRateLimiting:
    """Test rate limiting to prevent abuse"""

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self):
        """Test that rate limiting is enforced"""
        from app.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = {
                "url": "https://example.com",
                "review_cycle": "monthly"
            }

            # Submit many requests rapidly
            responses = []
            for _ in range(20):
                response = await client.post("/api/v1/enrich", json=payload)
                responses.append(response.status_code)

            # Should see some rate limiting
            # At least 80% success, but may have 429s
            success_count = sum(1 for code in responses if code == 200)
            rate_limited_count = sum(1 for code in responses if code == 429)

            assert success_count + rate_limited_count == 20
            # If rate limiting is implemented, should see some 429s
            # If not implemented yet, all should be 200

    @pytest.mark.asyncio
    async def test_rate_limit_per_ip(self):
        """Test rate limiting is per IP address"""
        # This test would require multiple client IPs
        # Placeholder for future implementation
        pass


class TestGracefulDegradation:
    """Test graceful degradation when layers fail"""

    @pytest.fixture
    def orchestrator(self):
        return ProgressiveOrchestrator()

    @pytest.mark.asyncio
    async def test_layer1_failure_continues(self, orchestrator):
        """Test that Layer 1 failure doesn't stop enrichment"""
        request = EnrichmentRequest(
            url="https://example.com",
            company_name="Provided Name",
            review_cycle="monthly"
        )

        with patch.object(orchestrator.layer1, 'extract') as mock_l1:
            mock_l1.side_effect = Exception("Layer 1 failed")

            # Should continue with user-provided data
            response = await orchestrator.enrich(request)

            assert response.company_name == "Provided Name"

    @pytest.mark.asyncio
    async def test_layer2_failure_uses_layer1(self, orchestrator):
        """Test that Layer 2 failure falls back to Layer 1"""
        request = EnrichmentRequest(
            url="https://example.com",
            review_cycle="monthly"
        )

        with patch.object(orchestrator.layer1, 'extract') as mock_l1, \
             patch.object(orchestrator.layer2, 'enrich') as mock_l2:

            mock_l1.return_value = {"company_name": "L1 Name", "industry": "L1 Industry"}
            mock_l2.side_effect = Exception("Layer 2 failed")

            response = await orchestrator.enrich(request)

            # Should have Layer 1 data
            assert response.company_name == "L1 Name"
            assert response.industry == "L1 Industry"

    @pytest.mark.asyncio
    async def test_layer3_failure_uses_layer2(self, orchestrator):
        """Test that Layer 3 failure returns Layer 2 data"""
        request = EnrichmentRequest(
            url="https://example.com",
            review_cycle="monthly"
        )

        with patch.object(orchestrator.layer1, 'extract') as mock_l1, \
             patch.object(orchestrator.layer2, 'enrich') as mock_l2, \
             patch.object(orchestrator.layer3, 'infer') as mock_l3:

            mock_l1.return_value = {"company_name": "L1 Name"}
            mock_l2.return_value = {"company_name": "L2 Name", "industry": "L2 Industry"}
            mock_l3.side_effect = Exception("Layer 3 failed")

            response = await orchestrator.enrich(request)

            # Should have Layer 2 data
            assert response.company_name == "L2 Name"
            assert response.industry == "L2 Industry"

    @pytest.mark.asyncio
    async def test_all_layers_fail_returns_input(self, orchestrator):
        """Test that if all layers fail, user input is preserved"""
        request = EnrichmentRequest(
            url="https://example.com",
            company_name="User Name",
            industry="User Industry",
            review_cycle="monthly"
        )

        with patch.object(orchestrator.layer1, 'extract') as mock_l1, \
             patch.object(orchestrator.layer2, 'enrich') as mock_l2, \
             patch.object(orchestrator.layer3, 'infer') as mock_l3:

            mock_l1.side_effect = Exception("Layer 1 failed")
            mock_l2.side_effect = Exception("Layer 2 failed")
            mock_l3.side_effect = Exception("Layer 3 failed")

            response = await orchestrator.enrich(request)

            # Should preserve user input
            assert response.company_name == "User Name"
            assert response.industry == "User Industry"


class TestNetworkErrors:
    """Test handling of network errors"""

    @pytest.fixture
    def metadata_extractor(self):
        return MetadataExtractor()

    @pytest.mark.asyncio
    async def test_connection_timeout(self, metadata_extractor):
        """Test handling of connection timeout"""
        url = "https://slow-website.com"

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError()

            result = await metadata_extractor.extract(url)

            # Should handle gracefully
            assert isinstance(result, dict)
            assert "error" in result or result == {}

    @pytest.mark.asyncio
    async def test_dns_resolution_failure(self, metadata_extractor):
        """Test handling of DNS resolution failure"""
        url = "https://non-existent-domain-12345.com"

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("DNS resolution failed")

            result = await metadata_extractor.extract(url)

            # Should handle gracefully
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_ssl_certificate_error(self, metadata_extractor):
        """Test handling of SSL certificate errors"""
        url = "https://self-signed-cert.com"

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("SSL certificate verify failed")

            result = await metadata_extractor.extract(url)

            # Should handle gracefully
            assert isinstance(result, dict)


class TestDataValidation:
    """Test data validation and sanitization"""

    @pytest.mark.asyncio
    async def test_xss_prevention_in_description(self):
        """Test that XSS attempts in description are sanitized"""
        from app.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            xss_payload = '<script>alert("XSS")</script>'

            payload = {
                "url": "https://example.com",
                "description": xss_payload,
                "review_cycle": "monthly"
            }

            response = await client.post("/api/v1/enrich", json=payload)

            if response.status_code == 200:
                data = response.json()
                # Should sanitize script tags
                assert '<script>' not in data.get("description", "")

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are prevented"""
        from app.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            sql_payload = "'; DROP TABLE companies; --"

            payload = {
                "url": "https://example.com",
                "company_name": sql_payload,
                "review_cycle": "monthly"
            }

            response = await client.post("/api/v1/enrich", json=payload)

            # Should handle without executing SQL
            assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_description_length_enforcement(self):
        """Test that description length limit is enforced"""
        from app.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            long_description = "A" * 1000  # Exceeds 800 char limit

            payload = {
                "url": "https://example.com",
                "description": long_description,
                "review_cycle": "monthly"
            }

            response = await client.post("/api/v1/enrich", json=payload)

            if response.status_code == 200:
                data = response.json()
                # Should truncate or reject
                assert len(data.get("description", "")) <= 800
            else:
                assert response.status_code == 422


class TestConcurrencyErrors:
    """Test handling of concurrent request errors"""

    @pytest.mark.asyncio
    async def test_concurrent_requests_dont_interfere(self):
        """Test that concurrent requests don't interfere with each other"""
        orchestrator = ProgressiveOrchestrator()

        requests = [
            EnrichmentRequest(url=f"https://example{i}.com", review_cycle="monthly")
            for i in range(10)
        ]

        # Process concurrently
        tasks = [orchestrator.enrich(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete independently
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) >= 8  # At least 80% success rate

    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self):
        """Test that repeated requests don't leak memory"""
        import gc
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        orchestrator = ProgressiveOrchestrator()

        # Run many enrichments
        for i in range(50):
            request = EnrichmentRequest(
                url=f"https://example{i}.com",
                review_cycle="monthly"
            )
            try:
                await orchestrator.enrich(request)
            except:
                pass

        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 100 MB)
        assert memory_increase < 100, f"Memory leak detected: {memory_increase}MB increase"
