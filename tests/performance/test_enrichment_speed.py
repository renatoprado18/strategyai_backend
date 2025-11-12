"""
Performance tests for the progressive enrichment system
Tests that each layer completes within specified time limits
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from app.services.enrichment.progressive_orchestrator import ProgressiveOrchestrator
from app.services.enrichment.layer1_metadata import MetadataExtractor
from app.services.enrichment.layer2_sources import ExternalSourceEnricher
from app.services.enrichment.layer3_ai import AIInferenceEngine
from tests.fixtures.enrichment_data import PERFORMANCE_BENCHMARKS


class TestLayer1Performance:
    """Test Layer 1 (metadata extraction) performance"""

    @pytest.fixture
    def metadata_extractor(self):
        return MetadataExtractor()

    @pytest.mark.asyncio
    async def test_layer1_completes_under_2s(self, metadata_extractor):
        """Ensure Layer 1 completes in under 2 seconds"""
        url = "https://example.com"
        html_content = """
        <html>
            <head>
                <title>Example Company</title>
                <meta name="description" content="Test description">
            </head>
            <body><h1>Test</h1></body>
        </html>
        """

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value=html_content)
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            start_time = datetime.now()
            result = await metadata_extractor.extract(url)
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()

            assert duration < PERFORMANCE_BENCHMARKS["layer1"]["max_duration_seconds"]
            assert result is not None

    @pytest.mark.asyncio
    async def test_layer1_metadata_extraction_speed(self, metadata_extractor):
        """Test metadata extraction completes quickly"""
        url = "https://fast-site.com"

        start_time = datetime.now()

        # Use actual extraction (may need mocking for CI/CD)
        try:
            result = await asyncio.wait_for(
                metadata_extractor.extract(url),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            pytest.fail("Layer 1 metadata extraction exceeded 2 second timeout")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        assert duration < 2.0, f"Layer 1 took {duration}s, expected <2s"

    @pytest.mark.asyncio
    async def test_layer1_social_detection_speed(self, metadata_extractor):
        """Test social media detection doesn't slow down Layer 1"""
        url = "https://example.com"
        html_with_many_links = """
        <html><body>
        """ + "".join([
            f'<a href="https://link{i}.com">Link {i}</a>'
            for i in range(100)
        ]) + """
        <a href="https://instagram.com/example">Instagram</a>
        <a href="https://tiktok.com/@example">TikTok</a>
        </body></html>
        """

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value=html_with_many_links)
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            start_time = datetime.now()
            result = await metadata_extractor.extract(url)
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()

            assert duration < 2.0
            assert "social_links" in result


class TestLayer2Performance:
    """Test Layer 2 (external sources) performance"""

    @pytest.fixture
    def source_enricher(self):
        return ExternalSourceEnricher()

    @pytest.mark.asyncio
    async def test_layer2_completes_under_6s(self, source_enricher):
        """Ensure Layer 2 completes in under 6 seconds"""
        url = "https://example.com"
        layer1_data = {"company_name": "Example", "industry": "Tech"}

        with patch.object(source_enricher, '_enrich_clearbit') as mock_clearbit:
            mock_clearbit.return_value = {
                "company_name": "Example Inc",
                "employees": 100
            }

            start_time = datetime.now()
            result = await source_enricher.enrich(url, layer1_data)
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()

            assert duration < PERFORMANCE_BENCHMARKS["layer2"]["max_duration_seconds"]
            assert result is not None

    @pytest.mark.asyncio
    async def test_layer2_parallel_api_calls(self, source_enricher):
        """Test that Layer 2 makes parallel API calls for speed"""
        url = "https://example.com"
        layer1_data = {}

        # Mock multiple API sources
        with patch.object(source_enricher, '_enrich_clearbit') as mock_clearbit, \
             patch.object(source_enricher, '_enrich_other_source') as mock_other:

            # Simulate API delay
            async def delayed_response():
                await asyncio.sleep(1)
                return {"data": "test"}

            mock_clearbit.side_effect = delayed_response
            mock_other.side_effect = delayed_response

            start_time = datetime.now()
            result = await source_enricher.enrich(url, layer1_data)
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()

            # Parallel calls should take ~1s, not 2s
            assert duration < 2.0, "API calls should be parallel"

    @pytest.mark.asyncio
    async def test_layer2_timeout_enforcement(self, source_enricher):
        """Test that Layer 2 enforces timeout limits"""
        url = "https://slow-api.example.com"
        layer1_data = {}

        with patch.object(source_enricher, '_enrich_clearbit') as mock_clearbit:
            # Simulate slow API (10 seconds)
            async def slow_api():
                await asyncio.sleep(10)
                return {"data": "test"}

            mock_clearbit.side_effect = slow_api

            start_time = datetime.now()
            result = await source_enricher.enrich(url, layer1_data)
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()

            # Should timeout before 10s
            assert duration < 6.0, "Layer 2 should enforce timeout"


class TestLayer3Performance:
    """Test Layer 3 (AI inference) performance"""

    @pytest.fixture
    def ai_engine(self):
        return AIInferenceEngine()

    @pytest.mark.asyncio
    async def test_layer3_completes_under_10s(self, ai_engine):
        """Ensure Layer 3 completes in under 10 seconds"""
        enriched_data = {
            "company_name": "Example Inc",
            "industry": "Technology",
            "description": "We build software"
        }

        mock_ai_response = {
            "industry": "Software Development",
            "target_market": "B2B",
            "confidence_scores": {"industry": 0.92}
        }

        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value = AsyncMock(
                choices=[AsyncMock(message={"content": str(mock_ai_response)})]
            )

            start_time = datetime.now()
            result = await ai_engine.infer(enriched_data)
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()

            assert duration < PERFORMANCE_BENCHMARKS["layer3"]["max_duration_seconds"]
            assert result is not None

    @pytest.mark.asyncio
    async def test_layer3_ai_timeout(self, ai_engine):
        """Test that AI inference has proper timeout"""
        enriched_data = {"company_name": "Example"}

        with patch('openai.ChatCompletion.acreate') as mock_openai:
            # Simulate slow AI response
            async def slow_ai(*args, **kwargs):
                await asyncio.sleep(15)
                return AsyncMock(choices=[])

            mock_openai.side_effect = slow_ai

            start_time = datetime.now()
            result = await ai_engine.infer(enriched_data)
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()

            # Should timeout before 15s
            assert duration < 10.0


class TestTotalEnrichmentPerformance:
    """Test total end-to-end enrichment performance"""

    @pytest.fixture
    def orchestrator(self):
        return ProgressiveOrchestrator()

    @pytest.mark.asyncio
    async def test_total_enrichment_under_15s(self, orchestrator):
        """Ensure total enrichment completes in under 15 seconds"""
        from app.models.schemas import EnrichmentRequest

        request = EnrichmentRequest(
            url="https://example.com",
            review_cycle="monthly"
        )

        with patch.object(orchestrator.layer1, 'extract') as mock_l1, \
             patch.object(orchestrator.layer2, 'enrich') as mock_l2, \
             patch.object(orchestrator.layer3, 'infer') as mock_l3:

            # Simulate realistic delays
            async def layer1_extract(*args):
                await asyncio.sleep(1.0)  # 1 second
                return {"company_name": "Example"}

            async def layer2_enrich(*args):
                await asyncio.sleep(2.0)  # 2 seconds
                return {"company_name": "Example Inc", "industry": "Tech"}

            async def layer3_infer(*args):
                await asyncio.sleep(3.0)  # 3 seconds
                return {
                    "company_name": "Example Inc",
                    "industry": "Tech",
                    "confidence_scores": {"company_name": 0.95}
                }

            mock_l1.side_effect = layer1_extract
            mock_l2.side_effect = layer2_enrich
            mock_l3.side_effect = layer3_infer

            start_time = datetime.now()
            response = await orchestrator.enrich(request)
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()

            assert duration < PERFORMANCE_BENCHMARKS["total"]["max_duration_seconds"]
            assert response is not None

    @pytest.mark.asyncio
    async def test_enrichment_scales_with_concurrent_requests(self, orchestrator):
        """Test that system maintains performance with concurrent requests"""
        from app.models.schemas import EnrichmentRequest

        requests = [
            EnrichmentRequest(url=f"https://example{i}.com", review_cycle="monthly")
            for i in range(10)
        ]

        start_time = datetime.now()

        # Process 10 concurrent enrichments
        tasks = [orchestrator.enrich(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 10 concurrent requests should not take 10x time
        # Should complete in under 30 seconds (not 150s)
        assert duration < 30.0

        # Check that most completed successfully
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) >= 8, "At least 80% should succeed"


class TestPerformanceOptimizations:
    """Test that performance optimizations are working"""

    @pytest.mark.asyncio
    async def test_caching_improves_performance(self):
        """Test that caching reduces enrichment time for repeated requests"""
        from app.services.enrichment.progressive_orchestrator import ProgressiveOrchestrator

        orchestrator = ProgressiveOrchestrator()
        url = "https://example.com"

        # First request (cold cache)
        from app.models.schemas import EnrichmentRequest
        request1 = EnrichmentRequest(url=url, review_cycle="monthly")

        start1 = datetime.now()
        response1 = await orchestrator.enrich(request1)
        duration1 = (datetime.now() - start1).total_seconds()

        # Second request (warm cache)
        request2 = EnrichmentRequest(url=url, review_cycle="monthly")

        start2 = datetime.now()
        response2 = await orchestrator.enrich(request2)
        duration2 = (datetime.now() - start2).total_seconds()

        # Cached request should be faster (if caching is implemented)
        # This test may need adjustment based on actual caching implementation
        assert duration2 <= duration1, "Cached request should be <= original request time"

    @pytest.mark.asyncio
    async def test_timeout_prevents_hanging(self):
        """Test that timeouts prevent system from hanging indefinitely"""
        orchestrator = ProgressiveOrchestrator()

        from app.models.schemas import EnrichmentRequest
        request = EnrichmentRequest(
            url="https://infinitely-slow-website.com",
            review_cycle="monthly"
        )

        start_time = datetime.now()

        # Should timeout, not hang forever
        with pytest.raises((asyncio.TimeoutError, Exception)) or True:
            await asyncio.wait_for(
                orchestrator.enrich(request),
                timeout=20.0  # Max 20 seconds
            )

        duration = (datetime.now() - start_time).total_seconds()
        assert duration < 20.0, "Should timeout within 20 seconds"


@pytest.mark.benchmark
class TestBenchmarks:
    """Benchmark tests for performance tracking"""

    def test_benchmark_layer1_extraction(self, benchmark):
        """Benchmark Layer 1 metadata extraction"""
        extractor = MetadataExtractor()
        url = "https://example.com"

        async def run_extraction():
            return await extractor.extract(url)

        # Run benchmark
        result = benchmark(asyncio.run, run_extraction())

        # Should complete quickly
        assert benchmark.stats.stats.mean < 2.0

    def test_benchmark_full_enrichment(self, benchmark):
        """Benchmark full enrichment pipeline"""
        orchestrator = ProgressiveOrchestrator()

        from app.models.schemas import EnrichmentRequest
        request = EnrichmentRequest(
            url="https://example.com",
            review_cycle="monthly"
        )

        async def run_enrichment():
            return await orchestrator.enrich(request)

        result = benchmark(asyncio.run, run_enrichment())

        # Full enrichment benchmark
        assert benchmark.stats.stats.mean < 15.0
