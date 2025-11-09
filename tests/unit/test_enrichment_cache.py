"""
Unit Tests for EnrichmentCache

Tests the 30-day TTL caching system with multi-layer caching strategy.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

from app.services.enrichment.cache import EnrichmentCache, _in_memory_cache
from app.services.enrichment.models import QuickEnrichmentData, DeepEnrichmentData, DataQualityTier


@pytest.fixture
def enrichment_cache():
    """Create fresh EnrichmentCache instance"""
    return EnrichmentCache()


@pytest.fixture
def sample_quick_data():
    """Sample quick enrichment data"""
    return QuickEnrichmentData(
        website="https://techstart.com.br",
        domain="techstart.com.br",
        company_name="TechStart Innovations",
        description="Innovative tech solutions",
        location="São Paulo, SP, Brazil",
        tech_stack=["React", "Next.js"],
        source_attribution={"company_name": "metadata", "location": "ip_api"},
        sources_called=["metadata", "ip_api"],
        completeness_score=35.0,
        confidence_score=65.0,
        data_quality_tier=DataQualityTier.MODERATE,
        total_cost_usd=0.0,
        quick_duration_ms=2150
    )


@pytest.fixture
def sample_deep_data():
    """Sample deep enrichment data"""
    return DeepEnrichmentData(
        website="https://techstart.com.br",
        domain="techstart.com.br",
        company_name="TechStart Innovations",
        cnpj="12.345.678/0001-99",
        employee_count="25-50",
        linkedin_followers=1247,
        rating=4.7,
        source_attribution={
            "company_name": "metadata",
            "cnpj": "receita_ws",
            "employee_count": "clearbit",
            "linkedin_followers": "proxycurl",
            "rating": "google_places"
        },
        sources_called=["metadata", "ip_api", "receita_ws", "clearbit", "google_places", "proxycurl"],
        completeness_score=94.0,
        confidence_score=89.0,
        data_quality_tier=DataQualityTier.EXCELLENT,
        total_cost_usd=0.15,
        quick_duration_ms=2150,
        deep_duration_ms=31400
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestEnrichmentCache:
    """Test EnrichmentCache functionality"""

    async def test_cache_key_generation(self, enrichment_cache):
        """Test cache key generation"""
        domain = "techstart.com.br"

        quick_key = enrichment_cache._generate_cache_key(domain, "quick")
        deep_key = enrichment_cache._generate_cache_key(domain, "deep")

        assert quick_key == "quick:techstart.com.br"
        assert deep_key == "deep:techstart.com.br"

    async def test_set_and_get_quick_enrichment(
        self, enrichment_cache, sample_quick_data, mock_supabase_client
    ):
        """Test setting and getting quick enrichment from cache"""
        domain = "techstart.com.br"

        # Mock Supabase insert
        mock_result = Mock()
        mock_result.data = [{"id": 123, "domain": domain}]
        mock_supabase_client.table().insert().execute.return_value = mock_result

        # Set cache
        await enrichment_cache.set_quick(domain, sample_quick_data, ttl_days=30)

        # Check in-memory cache was set
        cache_key = "quick:techstart.com.br"
        assert cache_key in _in_memory_cache
        assert _in_memory_cache[cache_key]["data"]["company_name"] == "TechStart Innovations"

    async def test_cache_expiration(self, enrichment_cache):
        """Test cache expiration logic"""
        domain = "techstart.com.br"
        cache_key = enrichment_cache._generate_cache_key(domain, "quick")

        # Set expired cache entry
        expired_time = datetime.now() - timedelta(days=1)
        _in_memory_cache[cache_key] = {
            "data": {"company_name": "Test"},
            "expires_at": expired_time
        }

        # Should return None for expired cache
        result = await enrichment_cache.get_quick(domain)
        assert result is None

    async def test_in_memory_cache_hit(self, enrichment_cache, sample_quick_data):
        """Test in-memory cache hit (fastest path)"""
        domain = "techstart.com.br"
        cache_key = "quick:techstart.com.br"

        # Set in-memory cache
        _in_memory_cache[cache_key] = {
            "data": sample_quick_data.dict(),
            "expires_at": datetime.now() + timedelta(days=30)
        }

        # Get from cache (should hit in-memory)
        result = await enrichment_cache.get_quick(domain)

        assert result is not None
        assert result.company_name == "TechStart Innovations"
        assert result.domain == "techstart.com.br"

    async def test_cache_miss_returns_none(self, enrichment_cache, mock_supabase_client):
        """Test cache miss returns None"""
        domain = "nonexistent.com"

        # Mock Supabase to return no data
        mock_result = Mock()
        mock_result.data = []
        mock_supabase_client.table().select().eq().execute.return_value = mock_result

        result = await enrichment_cache.get_quick(domain)
        assert result is None

    async def test_set_deep_enrichment(
        self, enrichment_cache, sample_deep_data, mock_supabase_client
    ):
        """Test setting deep enrichment data"""
        domain = "techstart.com.br"

        # Mock Supabase insert
        mock_result = Mock()
        mock_result.data = [{"id": 456, "domain": domain}]
        mock_supabase_client.table().insert().execute.return_value = mock_result

        # Set deep cache
        await enrichment_cache.set_deep(domain, sample_deep_data, ttl_days=30)

        # Verify Supabase was called with correct data
        assert mock_supabase_client.table.called

        # Check in-memory cache
        cache_key = "deep:techstart.com.br"
        assert cache_key in _in_memory_cache

    async def test_clear_expired_database_cache(
        self, enrichment_cache, mock_supabase_client
    ):
        """Test clearing expired cache from database"""
        # Mock Supabase delete
        mock_result = Mock()
        mock_result.data = [{"id": 1}, {"id": 2}, {"id": 3}]
        mock_supabase_client.table().delete().lt().execute.return_value = mock_result

        # Clear expired cache
        deleted_count = await enrichment_cache.clear_expired()

        assert deleted_count == 3
        assert mock_supabase_client.table().delete.called

    async def test_cache_ttl_customization(
        self, enrichment_cache, sample_quick_data, mock_supabase_client
    ):
        """Test custom TTL (time-to-live) values"""
        domain = "techstart.com.br"

        # Mock Supabase
        mock_result = Mock()
        mock_result.data = [{"id": 123}]
        mock_supabase_client.table().insert().execute.return_value = mock_result

        # Set cache with custom TTL (7 days)
        await enrichment_cache.set_quick(domain, sample_quick_data, ttl_days=7)

        # Verify expiration is set correctly
        cache_key = "quick:techstart.com.br"
        cached_entry = _in_memory_cache[cache_key]
        expires_at = cached_entry["expires_at"]

        # Should expire in approximately 7 days
        time_diff = expires_at - datetime.now()
        assert 6 <= time_diff.days <= 7

    async def test_concurrent_cache_access(
        self, enrichment_cache, sample_quick_data, mock_supabase_client
    ):
        """Test thread-safe concurrent cache access"""
        import asyncio

        domain = "techstart.com.br"

        # Mock Supabase
        mock_result = Mock()
        mock_result.data = [{"id": 123}]
        mock_supabase_client.table().insert().execute.return_value = mock_result

        # Set cache
        await enrichment_cache.set_quick(domain, sample_quick_data)

        # Concurrent reads
        results = await asyncio.gather(*[
            enrichment_cache.get_quick(domain)
            for _ in range(10)
        ])

        # All reads should succeed
        assert all(r is not None for r in results)
        assert all(r.company_name == "TechStart Innovations" for r in results)

    async def test_cache_size_limits(self, enrichment_cache):
        """Test in-memory cache doesn't grow unbounded"""
        # Note: Current implementation doesn't have size limits
        # This test documents that behavior

        # Add many entries
        for i in range(1000):
            _in_memory_cache[f"test:domain{i}.com"] = {
                "data": {"test": "data"},
                "expires_at": datetime.now() + timedelta(days=30)
            }

        # All entries should be in cache
        assert len(_in_memory_cache) >= 1000

        # TODO: Consider implementing LRU cache with size limit

    async def test_serialization_deserialization(
        self, enrichment_cache, sample_quick_data, mock_supabase_client
    ):
        """Test Pydantic model serialization/deserialization"""
        domain = "techstart.com.br"

        # Mock Supabase
        mock_result = Mock()
        mock_result.data = [{"id": 123}]
        mock_supabase_client.table().insert().execute.return_value = mock_result

        # Set cache (serializes Pydantic model)
        await enrichment_cache.set_quick(domain, sample_quick_data)

        # Get from cache (deserializes back to Pydantic model)
        result = await enrichment_cache.get_quick(domain)

        # Verify all fields match
        assert result.company_name == sample_quick_data.company_name
        assert result.completeness_score == sample_quick_data.completeness_score
        assert result.tech_stack == sample_quick_data.tech_stack

    async def test_cache_invalidation(self, enrichment_cache):
        """Test manual cache invalidation"""
        domain = "techstart.com.br"
        cache_key = "quick:techstart.com.br"

        # Set cache
        _in_memory_cache[cache_key] = {
            "data": {"company_name": "Test"},
            "expires_at": datetime.now() + timedelta(days=30)
        }

        # Clear entire cache
        _in_memory_cache.clear()

        # Cache should be empty
        assert len(_in_memory_cache) == 0

    async def test_different_cache_types_dont_collide(
        self, enrichment_cache, sample_quick_data, sample_deep_data, mock_supabase_client
    ):
        """Test quick and deep cache use different keys"""
        domain = "techstart.com.br"

        # Mock Supabase
        mock_result = Mock()
        mock_result.data = [{"id": 123}]
        mock_supabase_client.table().insert().execute.return_value = mock_result

        # Set both quick and deep cache
        await enrichment_cache.set_quick(domain, sample_quick_data)
        await enrichment_cache.set_deep(domain, sample_deep_data)

        # Both should be in cache with different keys
        assert "quick:techstart.com.br" in _in_memory_cache
        assert "deep:techstart.com.br" in _in_memory_cache

        # Get both
        quick_result = await enrichment_cache.get_quick(domain)
        deep_result = await enrichment_cache.get_deep(domain)

        # Verify they're different
        assert quick_result.completeness_score == 35.0
        assert deep_result.completeness_score == 94.0


@pytest.mark.unit
class TestCacheKeyGeneration:
    """Test cache key generation edge cases"""

    def test_cache_key_normalization(self):
        """Test domain normalization in cache keys"""
        cache = EnrichmentCache()

        # Different formats should produce same key
        key1 = cache._generate_cache_key("TechStart.com.br", "quick")
        key2 = cache._generate_cache_key("techstart.com.br", "quick")
        key3 = cache._generate_cache_key("TECHSTART.COM.BR", "quick")

        # All should be lowercase
        assert key1 == key2 == key3 == "quick:techstart.com.br"

    def test_cache_key_special_characters(self):
        """Test cache keys with special characters"""
        cache = EnrichmentCache()

        # Domains with subdomains
        key = cache._generate_cache_key("api.techstart.com.br", "deep")
        assert key == "deep:api.techstart.com.br"

        # Domains with dashes
        key = cache._generate_cache_key("tech-start.com", "quick")
        assert key == "quick:tech-start.com"


@pytest.mark.unit
class TestCachePerformance:
    """Test cache performance characteristics"""

    @pytest.mark.asyncio
    async def test_cache_hit_is_fast(self, enrichment_cache, sample_quick_data):
        """Test cache hits are significantly faster than misses"""
        import time

        domain = "techstart.com.br"
        cache_key = "quick:techstart.com.br"

        # Set in-memory cache
        _in_memory_cache[cache_key] = {
            "data": sample_quick_data.dict(),
            "expires_at": datetime.now() + timedelta(days=30)
        }

        # Measure cache hit time
        start = time.time()
        result = await enrichment_cache.get_quick(domain)
        elapsed = time.time() - start

        assert result is not None
        # Cache hit should be very fast (< 1ms)
        assert elapsed < 0.001

    @pytest.mark.asyncio
    async def test_cache_set_performance(
        self, enrichment_cache, sample_quick_data, mock_supabase_client
    ):
        """Test cache set operations complete quickly"""
        import time

        domain = "techstart.com.br"

        # Mock Supabase
        mock_result = Mock()
        mock_result.data = [{"id": 123}]
        mock_supabase_client.table().insert().execute.return_value = mock_result

        # Measure set time
        start = time.time()
        await enrichment_cache.set_quick(domain, sample_quick_data)
        elapsed = time.time() - start

        # Set should be reasonably fast (< 100ms with mocked DB)
        assert elapsed < 0.1
