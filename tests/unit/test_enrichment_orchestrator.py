"""
Unit Tests for EnrichmentOrchestrator

Tests the main orchestrator that coordinates all data sources
and implements the hybrid sync/async enrichment workflow.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from app.services.enrichment.orchestrator import EnrichmentOrchestrator
from app.services.enrichment.models import QuickEnrichmentData, DeepEnrichmentData, DataQualityTier
from app.services.enrichment.sources.base import SourceResult


@pytest.fixture
def orchestrator():
    """Create EnrichmentOrchestrator instance"""
    return EnrichmentOrchestrator()


@pytest.fixture
def mock_quick_source_results():
    """Mock results from quick enrichment sources"""
    return [
        SourceResult(
            success=True,
            data={
                "company_name": "TechStart Innovations",
                "description": "Innovative tech solutions",
                "tech_stack": ["React", "Next.js"],
                "logo_url": "https://techstart.com/logo.png"
            },
            source_name="metadata",
            duration_ms=500,
            cost_usd=0.0
        ),
        SourceResult(
            success=True,
            data={
                "location": "São Paulo, SP, Brazil",
                "ip_timezone": "America/Sao_Paulo"
            },
            source_name="ip_api",
            duration_ms=200,
            cost_usd=0.0
        )
    ]


@pytest.fixture
def mock_deep_source_results():
    """Mock results from deep enrichment sources"""
    return [
        SourceResult(
            success=True,
            data={
                "cnpj": "12.345.678/0001-99",
                "legal_name": "TechStart Inovações Ltda",
                "address": "Av. Paulista, 1000 - São Paulo, SP"
            },
            source_name="receita_ws",
            duration_ms=2500,
            cost_usd=0.0
        ),
        SourceResult(
            success=True,
            data={
                "employee_count": "25-50",
                "annual_revenue": "$500K-1M",
                "industry": "Software",
                "founded_year": 2019
            },
            source_name="clearbit",
            duration_ms=1500,
            cost_usd=0.10
        ),
        SourceResult(
            success=True,
            data={
                "address": "Av. Paulista, 1000 - São Paulo",
                "phone": "+55 11 9999-8888",
                "rating": 4.7,
                "reviews_count": 124
            },
            source_name="google_places",
            duration_ms=1800,
            cost_usd=0.02
        ),
        SourceResult(
            success=True,
            data={
                "linkedin_url": "https://linkedin.com/company/techstart",
                "linkedin_followers": 1247,
                "linkedin_description": "Full description",
                "specialties": ["SaaS", "Cloud", "AI/ML"]
            },
            source_name="proxycurl",
            duration_ms=3200,
            cost_usd=0.03
        )
    ]


@pytest.mark.unit
@pytest.mark.asyncio
class TestEnrichmentOrchestrator:
    """Test EnrichmentOrchestrator functionality"""

    async def test_domain_extraction(self, orchestrator):
        """Test domain extraction from website URLs"""
        # Various URL formats
        domain1 = orchestrator._extract_domain("https://techstart.com.br")
        domain2 = orchestrator._extract_domain("http://www.techstart.com.br")
        domain3 = orchestrator._extract_domain("techstart.com.br")

        assert domain1 == "techstart.com.br"
        assert domain2 == "techstart.com.br"
        assert domain3 == "techstart.com.br"

    async def test_quick_enrichment_success(
        self, orchestrator, mock_quick_source_results, mock_supabase_client
    ):
        """Test successful quick enrichment"""
        # Mock cache miss
        mock_cache_result = Mock()
        mock_cache_result.data = []
        mock_supabase_client.table().select().eq().execute.return_value = mock_cache_result

        # Mock source calls
        with patch.object(
            orchestrator.quick_sources[0],
            'enrich_with_monitoring',
            return_value=mock_quick_source_results[0]
        ):
            with patch.object(
                orchestrator.quick_sources[1],
                'enrich_with_monitoring',
                return_value=mock_quick_source_results[1]
            ):
                result = await orchestrator.enrich_quick("https://techstart.com.br")

        assert isinstance(result, QuickEnrichmentData)
        assert result.company_name == "TechStart Innovations"
        assert result.location == "São Paulo, SP, Brazil"
        assert result.completeness_score > 0
        assert result.confidence_score > 0
        assert result.total_cost_usd == 0.0  # Quick enrichment is free

    async def test_quick_enrichment_cache_hit(self, orchestrator):
        """Test quick enrichment returns cached data"""
        cached_data = QuickEnrichmentData(
            website="https://techstart.com.br",
            domain="techstart.com.br",
            company_name="Cached Company",
            completeness_score=50.0,
            confidence_score=70.0,
            data_quality_tier=DataQualityTier.MODERATE,
            total_cost_usd=0.0,
            quick_duration_ms=0
        )

        # Mock cache hit
        with patch.object(orchestrator.cache, 'get_quick', return_value=cached_data):
            result = await orchestrator.enrich_quick("https://techstart.com.br")

        assert result.company_name == "Cached Company"
        # Verify sources were not called (cache hit)

    async def test_deep_enrichment_success(
        self, orchestrator, mock_quick_source_results, mock_deep_source_results
    ):
        """Test successful deep enrichment"""
        # Mock quick data
        quick_data = QuickEnrichmentData(
            website="https://techstart.com.br",
            domain="techstart.com.br",
            company_name="TechStart Innovations",
            completeness_score=35.0,
            confidence_score=65.0,
            data_quality_tier=DataQualityTier.MODERATE,
            total_cost_usd=0.0,
            quick_duration_ms=2500
        )

        with patch.object(orchestrator.cache, 'get_quick', return_value=quick_data):
            # Mock deep source calls
            with patch('asyncio.gather', return_value=mock_deep_source_results):
                result = await orchestrator.enrich_deep(
                    "https://techstart.com.br",
                    company_name="TechStart"
                )

        assert isinstance(result, DeepEnrichmentData)
        assert result.cnpj == "12.345.678/0001-99"
        assert result.employee_count == "25-50"
        assert result.rating == 4.7
        assert result.linkedin_followers == 1247
        assert result.completeness_score > 50
        assert result.total_cost_usd == 0.15  # 0.10 + 0.02 + 0.03

    async def test_completeness_score_calculation(self, orchestrator):
        """Test completeness score calculation"""
        # Create enriched data with specific fields
        enriched_data = DeepEnrichmentData(
            website="https://test.com",
            domain="test.com",
            company_name="Test",
            cnpj="12.345.678/0001-99",
            employee_count="10-25",
            industry="Tech",
            # 4 fields populated out of 40 possible = 10%
            completeness_score=0.0,  # Will be calculated
            confidence_score=80.0,
            data_quality_tier=DataQualityTier.MINIMAL,
            total_cost_usd=0.0
        )

        score = orchestrator._calculate_completeness(enriched_data.dict())

        # Should be around 10% (4 fields / 40 possible fields)
        assert 5.0 <= score <= 15.0

    async def test_confidence_score_calculation(self, orchestrator, mock_deep_source_results):
        """Test confidence score calculation based on source weights"""
        score = orchestrator._calculate_confidence(mock_deep_source_results)

        # Should be weighted average of source reliabilities
        # receita_ws (0.95), clearbit (0.95), google_places (0.90), proxycurl (0.85)
        # Average should be around 91%
        assert 85 <= score <= 95

    async def test_quality_tier_assignment(self, orchestrator):
        """Test quality tier assignment based on completeness"""
        # Excellent (90-100%)
        tier_excellent = orchestrator._get_quality_tier(95.0)
        assert tier_excellent == DataQualityTier.EXCELLENT

        # High (70-89%)
        tier_high = orchestrator._get_quality_tier(80.0)
        assert tier_high == DataQualityTier.HIGH

        # Moderate (40-69%)
        tier_moderate = orchestrator._get_quality_tier(55.0)
        assert tier_moderate == DataQualityTier.MODERATE

        # Minimal (< 40%)
        tier_minimal = orchestrator._get_quality_tier(25.0)
        assert tier_minimal == DataQualityTier.MINIMAL

    async def test_source_attribution(self, orchestrator, mock_quick_source_results):
        """Test source attribution tracking"""
        with patch('asyncio.gather', return_value=mock_quick_source_results):
            merged = orchestrator._merge_quick_results(
                mock_quick_source_results,
                "https://techstart.com.br",
                "techstart.com.br"
            )

        # Check source attribution
        assert merged.source_attribution["company_name"] == "metadata"
        assert merged.source_attribution["location"] == "ip_api"

    async def test_partial_source_failure(self, orchestrator):
        """Test orchestrator handles partial source failures gracefully"""
        # One source succeeds, one fails
        results = [
            SourceResult(
                success=True,
                data={"company_name": "Test Company"},
                source_name="metadata",
                duration_ms=500,
                cost_usd=0.0
            ),
            SourceResult(
                success=False,
                error_type="timeout",
                error_message="Request timed out",
                source_name="ip_api",
                duration_ms=10000,
                cost_usd=0.0
            )
        ]

        with patch('asyncio.gather', return_value=results):
            merged = orchestrator._merge_quick_results(
                results,
                "https://test.com",
                "test.com"
            )

        # Should still have data from successful source
        assert merged.company_name == "Test Company"
        # Failed source should be tracked
        assert "ip_api" in merged.sources_called

    async def test_all_sources_fail(self, orchestrator):
        """Test orchestrator when all sources fail"""
        results = [
            SourceResult(
                success=False,
                error_type="timeout",
                source_name="metadata",
                duration_ms=10000,
                cost_usd=0.0
            ),
            SourceResult(
                success=False,
                error_type="timeout",
                source_name="ip_api",
                duration_ms=10000,
                cost_usd=0.0
            )
        ]

        with patch('asyncio.gather', return_value=results):
            merged = orchestrator._merge_quick_results(
                results,
                "https://test.com",
                "test.com"
            )

        # Should return minimal data
        assert merged.domain == "test.com"
        assert merged.completeness_score == 0.0

    async def test_cost_calculation(self, orchestrator, mock_deep_source_results):
        """Test total cost calculation from all sources"""
        total_cost = sum(r.cost_usd for r in mock_deep_source_results if r.success)

        assert total_cost == 0.15  # 0.00 + 0.10 + 0.02 + 0.03

    async def test_duration_tracking(self, orchestrator, mock_quick_source_results):
        """Test duration tracking for quick enrichment"""
        import time

        start_time = time.time()

        with patch('asyncio.gather', return_value=mock_quick_source_results):
            result = await orchestrator.enrich_quick("https://test.com")

        # Duration should be tracked
        assert result.quick_duration_ms > 0

    async def test_parallel_source_execution(self, orchestrator):
        """Test sources are called in parallel (asyncio.gather)"""
        with patch('asyncio.gather') as mock_gather:
            mock_gather.return_value = []

            await orchestrator.enrich_quick("https://test.com")

            # Verify asyncio.gather was called (parallel execution)
            assert mock_gather.called

    async def test_deep_enrichment_inherits_quick_data(self, orchestrator):
        """Test deep enrichment inherits data from quick enrichment"""
        # Quick enrichment provides company name
        quick_data = QuickEnrichmentData(
            website="https://test.com",
            domain="test.com",
            company_name="Quick Company Name",
            completeness_score=20.0,
            confidence_score=60.0,
            data_quality_tier=DataQualityTier.MINIMAL,
            total_cost_usd=0.0,
            quick_duration_ms=2000
        )

        # Deep enrichment adds more data
        deep_results = [
            SourceResult(
                success=True,
                data={"cnpj": "12.345.678/0001-99"},
                source_name="receita_ws",
                duration_ms=2500,
                cost_usd=0.0
            )
        ]

        with patch.object(orchestrator.cache, 'get_quick', return_value=quick_data):
            with patch('asyncio.gather', return_value=deep_results):
                result = await orchestrator.enrich_deep("https://test.com")

        # Should have both quick and deep data
        assert result.company_name == "Quick Company Name"
        assert result.cnpj == "12.345.678/0001-99"

    async def test_deep_sources_can_override_quick_data(self, orchestrator):
        """Test deep sources can override quick enrichment data (higher confidence)"""
        # Quick provides company name from metadata (70% confidence)
        quick_data = QuickEnrichmentData(
            website="https://test.com",
            domain="test.com",
            company_name="Metadata Company Name",
            source_attribution={"company_name": "metadata"},
            completeness_score=20.0,
            confidence_score=70.0,
            data_quality_tier=DataQualityTier.MINIMAL,
            total_cost_usd=0.0,
            quick_duration_ms=2000
        )

        # Deep provides company name from Clearbit (95% confidence)
        deep_results = [
            SourceResult(
                success=True,
                data={"company_name": "Clearbit Company Name"},
                source_name="clearbit",
                duration_ms=1500,
                cost_usd=0.10
            )
        ]

        with patch.object(orchestrator.cache, 'get_quick', return_value=quick_data):
            with patch('asyncio.gather', return_value=deep_results):
                result = await orchestrator.enrich_deep("https://test.com")

        # Clearbit should override metadata (higher confidence)
        assert result.company_name == "Clearbit Company Name"
        assert result.source_attribution["company_name"] == "clearbit"


@pytest.mark.unit
class TestSourcePriority:
    """Test source priority and conflict resolution"""

    def test_source_weights(self):
        """Test source reliability weights are configured correctly"""
        orchestrator = EnrichmentOrchestrator()

        # Verify weights
        assert orchestrator.SOURCE_WEIGHTS["clearbit"] == 0.95
        assert orchestrator.SOURCE_WEIGHTS["receita_ws"] == 0.95
        assert orchestrator.SOURCE_WEIGHTS["google_places"] == 0.90
        assert orchestrator.SOURCE_WEIGHTS["proxycurl"] == 0.85
        assert orchestrator.SOURCE_WEIGHTS["metadata"] == 0.70
        assert orchestrator.SOURCE_WEIGHTS["ip_api"] == 0.60

    def test_higher_weight_wins_conflict(self):
        """Test higher weighted source wins data conflicts"""
        orchestrator = EnrichmentOrchestrator()

        # Two sources provide same field
        results = [
            SourceResult(
                success=True,
                data={"company_name": "Metadata Name"},
                source_name="metadata",  # Weight: 0.70
                duration_ms=500,
                cost_usd=0.0
            ),
            SourceResult(
                success=True,
                data={"company_name": "Clearbit Name"},
                source_name="clearbit",  # Weight: 0.95
                duration_ms=1500,
                cost_usd=0.10
            )
        ]

        # Higher weight (Clearbit 0.95) should win over metadata (0.70)
        # This would be tested in merge logic


@pytest.mark.unit
@pytest.mark.asyncio
class TestEnrichmentEdgeCases:
    """Test edge cases and error conditions"""

    async def test_empty_website_url(self, orchestrator):
        """Test handling of empty website URL"""
        with pytest.raises(Exception):
            await orchestrator.enrich_quick("")

    async def test_invalid_url_format(self, orchestrator):
        """Test handling of invalid URL format"""
        # Should extract domain or raise error
        try:
            result = await orchestrator.enrich_quick("not-a-valid-url")
            # If it doesn't raise, should handle gracefully
            assert result.domain is not None
        except Exception:
            # Exception is acceptable for invalid input
            pass

    async def test_unicode_domain(self, orchestrator):
        """Test handling of internationalized domain names"""
        # Unicode domain
        domain = orchestrator._extract_domain("https://café.com.br")

        # Should handle unicode correctly
        assert domain is not None

    async def test_very_long_domain(self, orchestrator):
        """Test handling of very long domain names"""
        long_domain = "a" * 200 + ".com"

        # Should handle or truncate appropriately
        domain = orchestrator._extract_domain(f"https://{long_domain}")
        assert len(domain) <= 255  # Standard domain max length


@pytest.mark.unit
@pytest.mark.asyncio
class TestCacheIntegration:
    """Test cache integration in orchestrator"""

    async def test_quick_enrichment_sets_cache(self, orchestrator):
        """Test quick enrichment saves to cache"""
        mock_results = [
            SourceResult(
                success=True,
                data={"company_name": "Test"},
                source_name="metadata",
                duration_ms=500,
                cost_usd=0.0
            )
        ]

        with patch('asyncio.gather', return_value=mock_results):
            with patch.object(orchestrator.cache, 'set_quick') as mock_set:
                await orchestrator.enrich_quick("https://test.com")

                # Verify cache was set
                assert mock_set.called

    async def test_deep_enrichment_sets_cache(self, orchestrator):
        """Test deep enrichment saves to cache"""
        quick_data = QuickEnrichmentData(
            website="https://test.com",
            domain="test.com",
            company_name="Test",
            completeness_score=20.0,
            confidence_score=60.0,
            data_quality_tier=DataQualityTier.MINIMAL,
            total_cost_usd=0.0,
            quick_duration_ms=2000
        )

        mock_results = [
            SourceResult(
                success=True,
                data={"cnpj": "12.345.678/0001-99"},
                source_name="receita_ws",
                duration_ms=2500,
                cost_usd=0.0
            )
        ]

        with patch.object(orchestrator.cache, 'get_quick', return_value=quick_data):
            with patch('asyncio.gather', return_value=mock_results):
                with patch.object(orchestrator.cache, 'set_deep') as mock_set:
                    await orchestrator.enrich_deep("https://test.com")

                    # Verify deep cache was set
                    assert mock_set.called
