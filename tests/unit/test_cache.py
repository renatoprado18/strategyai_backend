"""
Unit tests for Cache System
Tests caching operations, key generation, and TTL management
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.core.cache import (
    generate_analysis_cache_key,
    generate_stage_cache_key,
    generate_content_hash,
    generate_pdf_cache_key,
    cache_analysis_result,
    get_cached_analysis,
    cache_stage_result,
    get_cached_stage_result,
    cache_pdf,
    get_cached_pdf,
    cache_dashboard_stats,
    get_cached_dashboard_stats
)


@pytest.mark.unit
class TestCacheKeyGeneration:
    """Test cache key generation functions"""

    def test_generate_analysis_cache_key_basic(self):
        """Test analysis cache key generation with basic inputs"""
        key1 = generate_analysis_cache_key(
            company="Test Company",
            industry="Technology",
            challenge="Grow revenue"
        )

        key2 = generate_analysis_cache_key(
            company="Test Company",
            industry="Technology",
            challenge="Grow revenue"
        )

        # Same inputs should generate same key
        assert key1 == key2
        assert key1.startswith("analysis:")

    def test_generate_analysis_cache_key_case_insensitive(self):
        """Test cache key is case-insensitive"""
        key1 = generate_analysis_cache_key(
            company="TEST COMPANY",
            industry="TECHNOLOGY",
            challenge="GROW REVENUE"
        )

        key2 = generate_analysis_cache_key(
            company="test company",
            industry="technology",
            challenge="grow revenue"
        )

        assert key1 == key2

    def test_generate_analysis_cache_key_different_challenges(self):
        """Test different challenges generate different keys"""
        key1 = generate_analysis_cache_key(
            company="Test Company",
            industry="Technology",
            challenge="Grow revenue by 100%"
        )

        key2 = generate_analysis_cache_key(
            company="Test Company",
            industry="Technology",
            challenge="Reduce costs by 50%"
        )

        assert key1 != key2

    def test_generate_analysis_cache_key_with_website(self):
        """Test cache key with website parameter"""
        key = generate_analysis_cache_key(
            company="Test Company",
            industry="Technology",
            challenge="Grow revenue",
            website="https://testcompany.com"
        )

        assert "analysis:" in key

    def test_generate_stage_cache_key(self):
        """Test stage cache key generation"""
        key1 = generate_stage_cache_key(
            stage_name="extraction",
            company="Test Company",
            industry="Technology",
            input_hash="abc123"
        )

        key2 = generate_stage_cache_key(
            stage_name="extraction",
            company="Test Company",
            industry="Technology",
            input_hash="abc123"
        )

        assert key1 == key2
        assert key1.startswith("stage:extraction:")

    def test_generate_content_hash_dict(self):
        """Test content hash generation for dictionary"""
        data1 = {"key": "value", "number": 123}
        data2 = {"key": "value", "number": 123}

        hash1 = generate_content_hash(data1)
        hash2 = generate_content_hash(data2)

        assert hash1 == hash2

    def test_generate_content_hash_bytes(self):
        """Test content hash generation for bytes"""
        data1 = b"test data"
        data2 = b"test data"

        hash1 = generate_content_hash(data1)
        hash2 = generate_content_hash(data2)

        assert hash1 == hash2

    def test_generate_pdf_cache_key(self):
        """Test PDF cache key generation"""
        report = {"test": "report", "data": [1, 2, 3]}

        key1 = generate_pdf_cache_key(report)
        key2 = generate_pdf_cache_key(report)

        assert key1 == key2
        assert key1.startswith("pdf:")


@pytest.mark.unit
class TestAnalysisCache:
    """Test analysis result caching"""

    @pytest.fixture
    def sample_analysis(self, sample_analysis_report):
        """Sample analysis result"""
        return sample_analysis_report

    @pytest.mark.asyncio
    async def test_cache_and_retrieve_analysis(self, mock_supabase_client, sample_analysis):
        """Test caching and retrieving analysis"""
        # Configure mock
        mock_result = Mock()
        mock_result.data = [{"id": 1}]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_result

        # Cache analysis
        success = await cache_analysis_result(
            company="Test Company",
            industry="Technology",
            challenge="Grow revenue",
            website="https://test.com",
            analysis_result=sample_analysis,
            cost=15.50,
            processing_time=45.2
        )

        assert success

    @pytest.mark.asyncio
    async def test_get_cached_analysis_miss(self, mock_supabase_client):
        """Test cache miss returns None"""
        # Configure mock for empty result
        mock_result = Mock()
        mock_result.data = []
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = mock_result

        result = await get_cached_analysis(
            company="Nonexistent Company",
            industry="Technology",
            challenge="Test",
            website=None
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_analysis_invalid_json(self, mock_supabase_client):
        """Test caching with invalid JSON fails gracefully"""
        # Create data that can't be JSON serialized
        class NonSerializable:
            pass

        invalid_data = {"test": NonSerializable()}

        success = await cache_analysis_result(
            company="Test",
            industry="Tech",
            challenge=None,
            website=None,
            analysis_result=invalid_data,
            cost=10.0,
            processing_time=30.0
        )

        # Should fail gracefully and return False
        assert not success


@pytest.mark.unit
class TestStageCache:
    """Test pipeline stage caching"""

    @pytest.mark.asyncio
    async def test_cache_stage_result(self, mock_supabase_client):
        """Test caching stage result"""
        mock_result = Mock()
        mock_result.data = [{"id": 1}]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_result

        input_data = {"key": "value"}
        stage_result = {"output": "result"}

        success = await cache_stage_result(
            stage_name="extraction",
            company="Test Company",
            industry="Technology",
            input_data=input_data,
            stage_result=stage_result,
            cost=2.50
        )

        assert success

    @pytest.mark.asyncio
    async def test_get_cached_stage_result_miss(self, mock_supabase_client):
        """Test stage cache miss returns None"""
        mock_result = Mock()
        mock_result.data = []
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = mock_result

        result = await get_cached_stage_result(
            stage_name="extraction",
            company="Test",
            industry="Tech",
            input_data={"key": "value"}
        )

        assert result is None


@pytest.mark.unit
class TestPDFCache:
    """Test PDF caching"""

    @pytest.mark.asyncio
    async def test_cache_pdf(self, mock_supabase_client, sample_analysis_report):
        """Test caching PDF"""
        mock_result = Mock()
        mock_result.data = [{"id": 1}]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_result

        pdf_bytes = b"PDF content here"

        success = await cache_pdf(
            report_json=sample_analysis_report,
            pdf_bytes=pdf_bytes,
            submission_id=123
        )

        assert success

    @pytest.mark.asyncio
    async def test_get_cached_pdf_miss(self):
        """Test PDF cache miss returns None"""
        result = await get_cached_pdf({"test": "report"})
        assert result is None


@pytest.mark.unit
class TestDashboardStatsCache:
    """Test dashboard statistics caching"""

    @pytest.mark.asyncio
    async def test_cache_dashboard_stats(self, mock_supabase_client):
        """Test caching dashboard stats"""
        stats = {
            "total_submissions": 100,
            "completed_analyses": 85,
            "average_cost": 12.50
        }

        success = await cache_dashboard_stats(stats)
        assert success

    @pytest.mark.asyncio
    async def test_get_cached_dashboard_stats_miss(self, mock_supabase_client):
        """Test stats cache miss returns None"""
        mock_result = Mock()
        mock_result.data = []
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = mock_result

        result = await get_cached_dashboard_stats()
        assert result is None


@pytest.mark.unit
class TestCacheErrorHandling:
    """Test cache error handling"""

    @pytest.mark.asyncio
    async def test_cache_handles_database_errors(self, mock_supabase_client):
        """Test cache operations handle database errors gracefully"""
        # Make Supabase throw an error
        mock_supabase_client.table.return_value.insert.side_effect = Exception("Database error")

        success = await cache_analysis_result(
            company="Test",
            industry="Tech",
            challenge=None,
            website=None,
            analysis_result={"test": "data"},
            cost=10.0,
            processing_time=30.0
        )

        # Should fail gracefully
        assert not success

    @pytest.mark.asyncio
    async def test_get_cache_handles_database_errors(self, mock_supabase_client):
        """Test cache retrieval handles database errors gracefully"""
        # Make Supabase throw an error
        mock_supabase_client.table.side_effect = Exception("Database error")

        result = await get_cached_analysis(
            company="Test",
            industry="Tech",
            challenge=None,
            website=None
        )

        # Should return None on error
        assert result is None
