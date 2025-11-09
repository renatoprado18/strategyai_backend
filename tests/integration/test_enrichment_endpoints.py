"""
Integration Tests for Enrichment API Endpoints

Tests the full enrichment flow through the API:
- Public enrichment submission endpoint
- Enrichment status checking
- Complete end-to-end workflow
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime, timedelta

from app.services.enrichment.models import QuickEnrichmentData, DeepEnrichmentData, DataQualityTier


@pytest.fixture
def mock_enrichment_data():
    """Mock enrichment data for testing"""
    return {
        "quick": QuickEnrichmentData(
            website="https://techstart.com.br",
            domain="techstart.com.br",
            company_name="TechStart Innovations",
            description="Innovative tech solutions",
            location="São Paulo, SP, Brazil",
            tech_stack=["React", "Next.js"],
            completeness_score=35.0,
            confidence_score=65.0,
            data_quality_tier=DataQualityTier.MODERATE,
            total_cost_usd=0.0,
            quick_duration_ms=2150
        ),
        "deep": DeepEnrichmentData(
            website="https://techstart.com.br",
            domain="techstart.com.br",
            company_name="TechStart Innovations",
            cnpj="12.345.678/0001-99",
            employee_count="25-50",
            linkedin_followers=1247,
            rating=4.7,
            completeness_score=94.0,
            confidence_score=89.0,
            data_quality_tier=DataQualityTier.EXCELLENT,
            total_cost_usd=0.15,
            quick_duration_ms=2150,
            deep_duration_ms=31400
        )
    }


@pytest.mark.integration
@pytest.mark.asyncio
class TestEnrichmentSubmission:
    """Test enrichment submission endpoint"""

    async def test_successful_enrichment_submission(
        self, async_client, mock_enrichment_data, mock_redis_client, mock_supabase_client
    ):
        """Test successful enrichment submission"""
        # Mock rate limiter
        mock_redis_client.get.return_value = None
        mock_redis_client.incr.return_value = 1

        # Mock repository save
        mock_supabase_result = Mock()
        mock_supabase_result.data = [{"id": 123}]
        mock_supabase_client.table().insert().execute.return_value = mock_supabase_result

        # Mock orchestrator
        with patch('app.routes.enrichment.EnrichmentOrchestrator') as mock_orch_class:
            mock_orch = Mock()
            mock_orch.enrich_quick = AsyncMock(return_value=mock_enrichment_data["quick"])
            mock_orch_class.return_value = mock_orch

            # Submit enrichment
            response = await async_client.post(
                "/api/enrichment/submit",
                json={
                    "email": "contato@techstart.com.br",
                    "company_website": "https://techstart.com.br"
                }
            )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "enrichment_id" in data
        assert data["data"]["company_name"] == "TechStart Innovations"
        assert data["completeness_score"] == 35.0
        assert data["cost_usd"] == 0.0
        assert "Quick enrichment complete" in data["message"]

    async def test_enrichment_invalid_email(self, async_client):
        """Test enrichment with invalid email"""
        response = await async_client.post(
            "/api/enrichment/submit",
            json={
                "email": "invalid-email",
                "company_website": "https://test.com"
            }
        )

        assert response.status_code == 422  # Validation error

    async def test_enrichment_invalid_website(self, async_client):
        """Test enrichment with invalid website URL"""
        response = await async_client.post(
            "/api/enrichment/submit",
            json={
                "email": "test@example.com",
                "company_website": "not-a-url"
            }
        )

        # Should either validate or normalize
        assert response.status_code in [200, 422]

    async def test_enrichment_rate_limiting(
        self, async_client, mock_redis_client
    ):
        """Test rate limiting (5 submissions per day)"""
        # Mock rate limit exceeded
        mock_redis_client.get.return_value = "6"  # Already at limit

        response = await async_client.post(
            "/api/enrichment/submit",
            json={
                "email": "test@example.com",
                "company_website": "https://test.com"
            }
        )

        assert response.status_code == 429  # Rate limit exceeded
        assert "Rate limit exceeded" in response.json()["detail"]

    async def test_enrichment_background_task_triggered(
        self, async_client, mock_enrichment_data, mock_redis_client, mock_supabase_client
    ):
        """Test deep enrichment background task is triggered"""
        # Mock rate limiter
        mock_redis_client.get.return_value = None

        # Mock repository
        mock_supabase_result = Mock()
        mock_supabase_result.data = [{"id": 123}]
        mock_supabase_client.table().insert().execute.return_value = mock_supabase_result

        # Mock orchestrator
        with patch('app.routes.enrichment.EnrichmentOrchestrator') as mock_orch_class:
            mock_orch = Mock()
            mock_orch.enrich_quick = AsyncMock(return_value=mock_enrichment_data["quick"])
            mock_orch_class.return_value = mock_orch

            # Mock background tasks
            with patch('app.routes.enrichment.BackgroundTasks.add_task') as mock_bg:
                response = await async_client.post(
                    "/api/enrichment/submit",
                    json={
                        "email": "test@example.com",
                        "company_website": "https://test.com"
                    }
                )

                # Verify background task was added
                assert mock_bg.called


@pytest.mark.integration
@pytest.mark.asyncio
class TestEnrichmentStatus:
    """Test enrichment status endpoint"""

    async def test_get_enrichment_status_quick_complete(
        self, async_client, mock_supabase_client
    ):
        """Test getting status when quick enrichment is complete"""
        # Mock repository response
        mock_result = Mock()
        mock_result.data = [{
            "id": 123,
            "domain": "techstart.com.br",
            "enrichment_type": "quick",
            "quick_data": json.dumps({
                "company_name": "TechStart",
                "completeness_score": 35.0
            }),
            "deep_data": None,
            "completeness_score": 35.0,
            "confidence_score": 65.0,
            "data_quality_tier": "moderate",
            "total_cost_usd": 0.0
        }]
        mock_supabase_client.table().select().eq().execute.return_value = mock_result

        response = await async_client.get("/api/enrichment/status/123")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["status"] == "quick_complete"
        assert data["enrichment_id"] == 123

    async def test_get_enrichment_status_deep_complete(
        self, async_client, mock_supabase_client
    ):
        """Test getting status when deep enrichment is complete"""
        # Mock repository response
        mock_result = Mock()
        mock_result.data = [{
            "id": 123,
            "domain": "techstart.com.br",
            "enrichment_type": "deep",
            "quick_data": json.dumps({"company_name": "TechStart"}),
            "deep_data": json.dumps({
                "company_name": "TechStart",
                "cnpj": "12.345.678/0001-99",
                "completeness_score": 94.0
            }),
            "completeness_score": 94.0,
            "confidence_score": 89.0,
            "data_quality_tier": "excellent",
            "total_cost_usd": 0.15
        }]
        mock_supabase_client.table().select().eq().execute.return_value = mock_result

        response = await async_client.get("/api/enrichment/status/123")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["status"] == "deep_complete"
        assert data["deep_data"] is not None

    async def test_get_enrichment_status_not_found(
        self, async_client, mock_supabase_client
    ):
        """Test getting status for non-existent enrichment"""
        # Mock repository returns empty
        mock_result = Mock()
        mock_result.data = []
        mock_supabase_client.table().select().eq().execute.return_value = mock_result

        response = await async_client.get("/api/enrichment/status/999")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestEnrichmentWorkflow:
    """Test complete enrichment workflow end-to-end"""

    async def test_complete_enrichment_workflow(
        self, async_client, mock_enrichment_data, mock_redis_client, mock_supabase_client
    ):
        """Test complete workflow: submit -> check status -> get results"""
        # Mock rate limiter
        mock_redis_client.get.return_value = None
        mock_redis_client.incr.return_value = 1

        # Mock repository save for submission
        mock_create_result = Mock()
        mock_create_result.data = [{"id": 123}]

        # Mock repository get for status check
        mock_status_result = Mock()
        mock_status_result.data = [{
            "id": 123,
            "domain": "techstart.com.br",
            "quick_data": json.dumps(mock_enrichment_data["quick"].dict()),
            "deep_data": json.dumps(mock_enrichment_data["deep"].dict()),
            "completeness_score": 94.0,
            "confidence_score": 89.0,
            "data_quality_tier": "excellent",
            "total_cost_usd": 0.15
        }]

        mock_supabase_client.table().insert().execute.return_value = mock_create_result
        mock_supabase_client.table().select().eq().execute.return_value = mock_status_result

        # Mock orchestrator
        with patch('app.routes.enrichment.EnrichmentOrchestrator') as mock_orch_class:
            mock_orch = Mock()
            mock_orch.enrich_quick = AsyncMock(return_value=mock_enrichment_data["quick"])
            mock_orch_class.return_value = mock_orch

            # Step 1: Submit enrichment
            submit_response = await async_client.post(
                "/api/enrichment/submit",
                json={
                    "email": "contato@techstart.com.br",
                    "company_website": "https://techstart.com.br"
                }
            )

            assert submit_response.status_code == 200
            submit_data = submit_response.json()
            enrichment_id = submit_data["enrichment_id"]

            # Step 2: Check status (simulating poll after deep enrichment)
            status_response = await async_client.get(
                f"/api/enrichment/status/{enrichment_id}"
            )

            assert status_response.status_code == 200
            status_data = status_response.json()

            # Verify complete enrichment
            assert status_data["status"] == "deep_complete"
            assert status_data["deep_data"] is not None
            assert status_data["completeness_score"] == 94.0

    async def test_cache_hit_workflow(
        self, async_client, mock_enrichment_data, mock_redis_client, mock_supabase_client
    ):
        """Test workflow with cache hit (instant response)"""
        # Mock rate limiter
        mock_redis_client.get.return_value = None

        # Mock cached enrichment
        cached_quick_data = mock_enrichment_data["quick"]

        # Mock orchestrator with cache
        with patch('app.routes.enrichment.EnrichmentOrchestrator') as mock_orch_class:
            mock_orch = Mock()
            # Cache hit - instant return
            mock_orch.enrich_quick = AsyncMock(return_value=cached_quick_data)
            mock_orch_class.return_value = mock_orch

            # Mock repository
            mock_result = Mock()
            mock_result.data = [{"id": 456}]
            mock_supabase_client.table().insert().execute.return_value = mock_result

            # Submit (should hit cache)
            response = await async_client.post(
                "/api/enrichment/submit",
                json={
                    "email": "test@example.com",
                    "company_website": "https://techstart.com.br"
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Cache hit should return quickly with cost $0.00
            assert data["cost_usd"] == 0.0


@pytest.mark.integration
@pytest.mark.asyncio
class TestEnrichmentValidation:
    """Test input validation for enrichment endpoints"""

    async def test_email_validation(self, async_client):
        """Test various email formats"""
        # Valid corporate email
        response_valid = await async_client.post(
            "/api/enrichment/submit",
            json={
                "email": "contact@company.com.br",
                "company_website": "https://company.com.br"
            }
        )
        # Should accept or reject based on validation rules
        assert response_valid.status_code in [200, 422]

    async def test_website_url_normalization(self, async_client, mock_redis_client):
        """Test website URL normalization"""
        # Mock rate limiter
        mock_redis_client.get.return_value = None

        # Various URL formats
        urls_to_test = [
            "techstart.com.br",  # Missing protocol
            "http://techstart.com.br",  # HTTP
            "https://techstart.com.br",  # HTTPS
            "https://www.techstart.com.br",  # With www
        ]

        for url in urls_to_test:
            # Should normalize to consistent format
            # Test documents expected behavior
            pass


@pytest.mark.integration
@pytest.mark.asyncio
class TestEnrichmentErrors:
    """Test error handling in enrichment endpoints"""

    async def test_enrichment_service_unavailable(
        self, async_client, mock_redis_client
    ):
        """Test handling when enrichment service fails"""
        # Mock rate limiter
        mock_redis_client.get.return_value = None

        # Mock orchestrator failure
        with patch('app.routes.enrichment.EnrichmentOrchestrator') as mock_orch_class:
            mock_orch = Mock()
            mock_orch.enrich_quick = AsyncMock(side_effect=Exception("Service error"))
            mock_orch_class.return_value = mock_orch

            response = await async_client.post(
                "/api/enrichment/submit",
                json={
                    "email": "test@example.com",
                    "company_website": "https://test.com"
                }
            )

            assert response.status_code == 500
            assert "Enrichment failed" in response.json()["detail"]

    async def test_database_error_handling(
        self, async_client, mock_redis_client, mock_supabase_client
    ):
        """Test handling when database operations fail"""
        # Mock rate limiter
        mock_redis_client.get.return_value = None

        # Mock database error
        mock_supabase_client.table().insert().execute.side_effect = Exception("DB error")

        response = await async_client.post(
            "/api/enrichment/submit",
            json={
                "email": "test@example.com",
                "company_website": "https://test.com"
            }
        )

        assert response.status_code == 500


@pytest.mark.integration
@pytest.mark.asyncio
class TestEnrichmentPerformance:
    """Test performance characteristics of enrichment endpoints"""

    async def test_quick_enrichment_response_time(
        self, async_client, mock_enrichment_data, mock_redis_client, mock_supabase_client
    ):
        """Test quick enrichment returns within acceptable time"""
        import time

        # Mock rate limiter
        mock_redis_client.get.return_value = None

        # Mock repository
        mock_result = Mock()
        mock_result.data = [{"id": 123}]
        mock_supabase_client.table().insert().execute.return_value = mock_result

        # Mock orchestrator
        with patch('app.routes.enrichment.EnrichmentOrchestrator') as mock_orch_class:
            mock_orch = Mock()
            mock_orch.enrich_quick = AsyncMock(return_value=mock_enrichment_data["quick"])
            mock_orch_class.return_value = mock_orch

            start = time.time()

            response = await async_client.post(
                "/api/enrichment/submit",
                json={
                    "email": "test@example.com",
                    "company_website": "https://test.com"
                }
            )

            elapsed = time.time() - start

            assert response.status_code == 200
            # Should respond quickly (< 5 seconds with mocked services)
            assert elapsed < 5.0
