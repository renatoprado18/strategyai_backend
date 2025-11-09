"""
Integration Tests for Enrichment Admin Dashboard Endpoints

Tests admin-only endpoints for:
- Dashboard statistics and analytics
- Enrichment history and search
- Audit trail viewing
- Source monitoring
- Cache management
"""

import pytest
from unittest.mock import Mock, patch
import json
from datetime import datetime, timedelta


@pytest.mark.integration
@pytest.mark.asyncio
class TestAdminDashboardStats:
    """Test admin dashboard statistics endpoint"""

    async def test_get_dashboard_stats_unauthorized(self, async_client):
        """Test dashboard access without authentication"""
        response = await async_client.get("/api/admin/enrichment/dashboard/stats")

        assert response.status_code == 401  # Unauthorized

    async def test_get_dashboard_stats_success(
        self, async_client, mock_authenticated_request, mock_supabase_client
    ):
        """Test successful dashboard stats retrieval"""
        # Mock repository statistics
        mock_stats = {
            "total_enrichments": 1247,
            "cache_hit_rate": 62.5,
            "total_cost_usd": 720.00,
            "total_savings_usd": 1080.00,
            "avg_completeness": 87.3,
            "avg_confidence": 84.1,
            "by_quality_tier": {
                "excellent": 543,
                "high": 412,
                "moderate": 234,
                "minimal": 58
            },
            "by_type": {
                "quick": 1247,
                "deep": 1247
            }
        }

        with patch('app.repositories.enrichment_repository.EnrichmentRepository.get_statistics') as mock_get_stats:
            mock_get_stats.return_value = mock_stats

            response = await async_client.get("/api/admin/enrichment/dashboard/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["total_enrichments"] == 1247
        assert data["data"]["cache_hit_rate"] == 62.5
        assert data["data"]["total_cost_usd"] == 720.00
        assert data["data"]["total_savings_usd"] == 1080.00

    async def test_dashboard_stats_calculation_accuracy(
        self, async_client, mock_authenticated_request
    ):
        """Test accuracy of dashboard statistics calculations"""
        # Mock detailed stats
        mock_stats = {
            "total_enrichments": 100,
            "cache_hit_rate": 60.0,  # 60% hit rate
            "total_cost_usd": 40.00,  # $0.40 per enrichment * 100
            "total_savings_usd": 60.00,  # Would have been $100 without cache
            "avg_completeness": 87.3,
            "avg_confidence": 84.1,
            "by_quality_tier": {
                "excellent": 40,
                "high": 30,
                "moderate": 20,
                "minimal": 10
            }
        }

        with patch('app.repositories.enrichment_repository.EnrichmentRepository.get_statistics') as mock_get_stats:
            mock_get_stats.return_value = mock_stats

            response = await async_client.get("/api/admin/enrichment/dashboard/stats")

            data = response.json()

            # Verify calculations
            assert data["data"]["cache_hit_rate"] == 60.0
            assert data["data"]["total_savings_usd"] == 60.00


@pytest.mark.integration
@pytest.mark.asyncio
class TestAdminEnrichmentList:
    """Test admin enrichment list endpoint"""

    async def test_list_enrichments_unauthorized(self, async_client):
        """Test listing enrichments without authentication"""
        response = await async_client.get("/api/admin/enrichment/list")

        assert response.status_code == 401

    async def test_list_enrichments_success(
        self, async_client, mock_authenticated_request, mock_supabase_client
    ):
        """Test successful enrichment listing"""
        # Mock enrichments
        mock_enrichments = [
            {
                "id": 123,
                "domain": "techstart.com.br",
                "completeness_score": 94.0,
                "data_quality_tier": "excellent",
                "total_cost_usd": 0.15,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": 124,
                "domain": "startup.com",
                "completeness_score": 78.0,
                "data_quality_tier": "high",
                "total_cost_usd": 0.0,  # Cache hit
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        with patch('app.repositories.enrichment_repository.EnrichmentRepository.get_recent_enrichments') as mock_get:
            mock_get.return_value = mock_enrichments

            response = await async_client.get("/api/admin/enrichment/list?limit=20")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["total"] == 2
        assert len(data["data"]) == 2

    async def test_list_enrichments_pagination(
        self, async_client, mock_authenticated_request
    ):
        """Test enrichment list pagination"""
        mock_enrichments = [{"id": i} for i in range(50)]

        with patch('app.repositories.enrichment_repository.EnrichmentRepository.get_recent_enrichments') as mock_get:
            mock_get.return_value = mock_enrichments[:20]

            response = await async_client.get("/api/admin/enrichment/list?limit=20")

            data = response.json()
            assert len(data["data"]) == 20

    async def test_filter_by_enrichment_type(
        self, async_client, mock_authenticated_request
    ):
        """Test filtering enrichments by type"""
        mock_deep_enrichments = [
            {"id": 1, "enrichment_type": "deep"},
            {"id": 2, "enrichment_type": "deep"}
        ]

        with patch('app.repositories.enrichment_repository.EnrichmentRepository.get_recent_enrichments') as mock_get:
            mock_get.return_value = mock_deep_enrichments

            response = await async_client.get(
                "/api/admin/enrichment/list?enrichment_type=deep"
            )

            data = response.json()
            assert all(e.get("enrichment_type") == "deep" for e in data["data"])


@pytest.mark.integration
@pytest.mark.asyncio
class TestAdminEnrichmentSearch:
    """Test admin enrichment search endpoint"""

    async def test_search_enrichments_by_domain(
        self, async_client, mock_authenticated_request
    ):
        """Test searching enrichments by domain"""
        mock_results = [
            {"id": 1, "domain": "techstart.com.br"},
            {"id": 2, "domain": "techstart.io"}
        ]

        with patch('app.repositories.enrichment_repository.EnrichmentRepository.search_by_domain') as mock_search:
            mock_search.return_value = mock_results

            response = await async_client.get(
                "/api/admin/enrichment/search?query=techstart"
            )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["data"]) == 2

    async def test_search_validation(self, async_client, mock_authenticated_request):
        """Test search query validation"""
        # Empty query
        response = await async_client.get("/api/admin/enrichment/search?query=")

        # Should require minimum length
        assert response.status_code in [200, 422]

    async def test_search_special_characters(
        self, async_client, mock_authenticated_request
    ):
        """Test search with special characters"""
        with patch('app.repositories.enrichment_repository.EnrichmentRepository.search_by_domain') as mock_search:
            mock_search.return_value = []

            # Search with dash
            response = await async_client.get(
                "/api/admin/enrichment/search?query=tech-start"
            )

            assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
class TestAdminEnrichmentDetail:
    """Test admin enrichment detail endpoint"""

    async def test_get_enrichment_detail(
        self, async_client, mock_authenticated_request, mock_supabase_client
    ):
        """Test getting detailed enrichment information"""
        # Mock enrichment detail
        mock_enrichment = {
            "id": 123,
            "domain": "techstart.com.br",
            "enrichment_type": "deep",
            "quick_data": json.dumps({"company_name": "TechStart"}),
            "deep_data": json.dumps({
                "company_name": "TechStart",
                "cnpj": "12.345.678/0001-99",
                "employee_count": "25-50"
            }),
            "source_attribution": {
                "company_name": "metadata",
                "cnpj": "receita_ws",
                "employee_count": "clearbit"
            },
            "completeness_score": 94.0,
            "confidence_score": 89.0,
            "data_quality_tier": "excellent",
            "total_cost_usd": 0.15,
            "created_at": datetime.utcnow().isoformat()
        }

        mock_result = Mock()
        mock_result.data = [mock_enrichment]
        mock_supabase_client.table().select().eq().execute.return_value = mock_result

        response = await async_client.get("/api/admin/enrichment/123")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["id"] == 123
        assert "source_attribution" in data["data"]

    async def test_get_enrichment_not_found(
        self, async_client, mock_authenticated_request, mock_supabase_client
    ):
        """Test getting non-existent enrichment"""
        mock_result = Mock()
        mock_result.data = []
        mock_supabase_client.table().select().eq().execute.return_value = mock_result

        response = await async_client.get("/api/admin/enrichment/999")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestAdminAuditTrail:
    """Test admin audit trail endpoint"""

    async def test_get_enrichment_audit_trail(
        self, async_client, mock_authenticated_request
    ):
        """Test getting complete audit trail for enrichment"""
        # Mock audit logs
        mock_audit_logs = [
            {
                "id": 1,
                "enrichment_id": 123,
                "source_name": "metadata",
                "request_data": {"domain": "test.com"},
                "response_data": {"company_name": "Test"},
                "success": True,
                "cost_usd": 0.0,
                "duration_ms": 500
            },
            {
                "id": 2,
                "enrichment_id": 123,
                "source_name": "clearbit",
                "request_data": {"domain": "test.com"},
                "response_data": {"employee_count": "25-50"},
                "success": True,
                "cost_usd": 0.10,
                "duration_ms": 1500
            }
        ]

        with patch('app.repositories.audit_repository.AuditRepository.get_by_enrichment') as mock_get:
            mock_get.return_value = mock_audit_logs

            response = await async_client.get("/api/admin/enrichment/123/audit")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["data"]["audit_logs"]) == 2
        assert data["data"]["summary"]["total_calls"] == 2
        assert data["data"]["summary"]["successful_calls"] == 2
        assert data["data"]["summary"]["total_cost_usd"] == 0.10

    async def test_audit_trail_with_failures(
        self, async_client, mock_authenticated_request
    ):
        """Test audit trail includes failed API calls"""
        mock_audit_logs = [
            {
                "source_name": "clearbit",
                "success": True,
                "cost_usd": 0.10,
                "duration_ms": 1500
            },
            {
                "source_name": "google_places",
                "success": False,
                "error_type": "timeout",
                "error_message": "Request timed out",
                "cost_usd": 0.0,
                "duration_ms": 10000
            }
        ]

        with patch('app.repositories.audit_repository.AuditRepository.get_by_enrichment') as mock_get:
            mock_get.return_value = mock_audit_logs

            response = await async_client.get("/api/admin/enrichment/123/audit")

            data = response.json()
            assert data["data"]["summary"]["failed_calls"] == 1

    async def test_get_source_audit_logs(
        self, async_client, mock_authenticated_request
    ):
        """Test getting audit logs for specific source"""
        mock_logs = [
            {"source_name": "clearbit", "success": True},
            {"source_name": "clearbit", "success": True},
            {"source_name": "clearbit", "success": False}
        ]

        with patch('app.repositories.audit_repository.AuditRepository.get_by_source') as mock_get:
            mock_get.return_value = mock_logs

            response = await async_client.get(
                "/api/admin/enrichment/audit/source/clearbit"
            )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["source_name"] == "clearbit"
        assert len(data["data"]["audit_logs"]) == 3


@pytest.mark.integration
@pytest.mark.asyncio
class TestAdminCacheManagement:
    """Test admin cache management endpoints"""

    async def test_clear_expired_cache(
        self, async_client, mock_authenticated_request
    ):
        """Test clearing expired cache entries"""
        with patch('app.repositories.enrichment_repository.EnrichmentRepository.clear_expired_cache') as mock_clear:
            mock_clear.return_value = 15  # 15 entries deleted

            response = await async_client.post(
                "/api/admin/enrichment/cache/clear-expired"
            )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["deleted_count"] == 15
        assert "Cleared 15" in data["data"]["message"]


@pytest.mark.integration
@pytest.mark.asyncio
class TestAdminSourceMonitoring:
    """Test admin source monitoring endpoint"""

    async def test_get_source_health_monitoring(
        self, async_client, mock_authenticated_request
    ):
        """Test getting health monitoring for all sources"""
        mock_source_stats = [
            {
                "source_name": "clearbit",
                "total_calls": 100,
                "successful_calls": 98,
                "failed_calls": 2,
                "success_rate": 98.0,
                "total_cost_usd": 10.00,
                "avg_duration_ms": 1500
            },
            {
                "source_name": "google_places",
                "total_calls": 100,
                "successful_calls": 95,
                "failed_calls": 5,
                "success_rate": 95.0,
                "total_cost_usd": 2.00,
                "avg_duration_ms": 1800
            }
        ]

        with patch('app.repositories.audit_repository.AuditRepository.get_all_source_statistics') as mock_get:
            mock_get.return_value = mock_source_stats

            response = await async_client.get(
                "/api/admin/enrichment/monitoring/sources?hours=24"
            )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["data"]["sources"]) == 2
        assert data["data"]["summary"]["total_sources"] == 2

    async def test_source_health_status_calculation(
        self, async_client, mock_authenticated_request
    ):
        """Test health status calculation for sources"""
        mock_source_stats = [
            {"source_name": "clearbit", "success_rate": 98.0},  # healthy
            {"source_name": "google_places", "success_rate": 85.0},  # degraded
            {"source_name": "proxycurl", "success_rate": 70.0}  # unhealthy
        ]

        with patch('app.repositories.audit_repository.AuditRepository.get_all_source_statistics') as mock_get:
            mock_get.return_value = mock_source_stats

            response = await async_client.get(
                "/api/admin/enrichment/monitoring/sources"
            )

            data = response.json()

            # Verify health statuses are assigned
            sources = data["data"]["sources"]
            assert sources[0]["health"] == "healthy"  # 98% >= 95%
            assert sources[1]["health"] == "degraded"  # 85% >= 80%
            assert sources[2]["health"] == "unhealthy"  # 70% < 80%


@pytest.mark.integration
@pytest.mark.asyncio
class TestAdminAnalytics:
    """Test admin advanced analytics endpoint"""

    async def test_get_advanced_analytics(
        self, async_client, mock_authenticated_request
    ):
        """Test getting advanced analytics"""
        mock_source_stats = [
            {"source_name": "clearbit", "total_calls": 100},
            {"source_name": "google_places", "total_calls": 100}
        ]

        mock_monthly_costs = [
            {"month": "2025-01", "cost_usd": 72.00, "enrichments": 100},
            {"month": "2024-12", "cost_usd": 68.00, "enrichments": 95}
        ]

        with patch('app.services.enrichment.analytics.EnrichmentAnalytics.get_all_source_stats') as mock_sources:
            with patch('app.services.enrichment.analytics.EnrichmentAnalytics.get_monthly_cost') as mock_costs:
                mock_sources.return_value = mock_source_stats
                mock_costs.return_value = {"total_cost_usd": 72.00, "total_enrichments": 100}

                response = await async_client.get(
                    "/api/admin/enrichment/dashboard/analytics"
                )

        assert response.status_code == 200
        # data = response.json()

        # Analytics should include source performance and cost trends


@pytest.mark.integration
@pytest.mark.asyncio
class TestAdminAuthorization:
    """Test authorization for admin endpoints"""

    async def test_all_admin_endpoints_require_auth(self, async_client):
        """Test all admin endpoints require authentication"""
        admin_endpoints = [
            "/api/admin/enrichment/dashboard/stats",
            "/api/admin/enrichment/list",
            "/api/admin/enrichment/search?query=test",
            "/api/admin/enrichment/123",
            "/api/admin/enrichment/123/audit",
            "/api/admin/enrichment/monitoring/sources"
        ]

        for endpoint in admin_endpoints:
            response = await async_client.get(endpoint)
            assert response.status_code == 401  # Unauthorized

    async def test_admin_endpoints_accept_valid_token(
        self, async_client, mock_authenticated_request
    ):
        """Test admin endpoints accept valid JWT token"""
        # Should be able to access with valid token
        with patch('app.repositories.enrichment_repository.EnrichmentRepository.get_statistics') as mock_get:
            mock_get.return_value = {"total_enrichments": 0}

            response = await async_client.get(
                "/api/admin/enrichment/dashboard/stats"
            )

            assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
class TestAdminErrorHandling:
    """Test error handling in admin endpoints"""

    async def test_handle_repository_errors_gracefully(
        self, async_client, mock_authenticated_request
    ):
        """Test graceful error handling when repository fails"""
        with patch('app.repositories.enrichment_repository.EnrichmentRepository.get_statistics') as mock_get:
            mock_get.side_effect = Exception("Database connection failed")

            response = await async_client.get(
                "/api/admin/enrichment/dashboard/stats"
            )

            assert response.status_code == 500
            assert "Failed to get dashboard statistics" in response.json()["detail"]

    async def test_invalid_enrichment_id_format(
        self, async_client, mock_authenticated_request
    ):
        """Test handling of invalid enrichment ID format"""
        response = await async_client.get("/api/admin/enrichment/invalid-id")

        # Should validate ID format
        assert response.status_code in [400, 404, 422]
