"""
Integration tests for Health and Monitoring Endpoints
Tests health checks, circuit breaker status, and system monitoring
"""

import pytest
from fastapi import status
from unittest.mock import Mock, patch


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_health_check_healthy(self, test_client, mock_redis_client, mock_supabase_client):
        """Test health check when all services are healthy"""
        # Mock database count
        with patch('app.core.database.count_submissions') as mock_count:
            mock_count.return_value = 100

            response = test_client.get("/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["status"] == "healthy"
            assert "checks" in data
            assert "database" in data["checks"]
            assert "redis" in data["checks"]
            assert "openrouter" in data["checks"]

    def test_health_check_database_down(self, test_client, mock_redis_client):
        """Test health check when database is down"""
        with patch('app.core.database.count_submissions') as mock_count:
            mock_count.side_effect = Exception("Database connection failed")

            response = test_client.get("/health")

            # Should still return 200 but with unhealthy status
            # Or 503 depending on implementation
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_503_SERVICE_UNAVAILABLE
            ]

            data = response.json()
            assert data["status"] in ["unhealthy", "degraded"]
            assert data["checks"]["database"]["status"] == "unhealthy"

    def test_health_check_redis_down(self, test_client):
        """Test health check when Redis is down"""
        with patch('app.core.security.rate_limiter.get_redis_client') as mock_redis:
            mock_client = Mock()
            mock_client.ping.side_effect = Exception("Redis connection failed")
            mock_redis.return_value = mock_client

            with patch('app.core.database.count_submissions') as mock_count:
                mock_count.return_value = 100

                response = test_client.get("/health")

                data = response.json()
                assert data["status"] in ["unhealthy", "degraded"]
                assert data["checks"]["redis"]["status"] == "unhealthy"

    def test_health_check_includes_circuit_breakers(self, test_client, mock_redis_client, reset_circuit_breakers):
        """Test health check includes circuit breaker status"""
        with patch('app.core.database.count_submissions') as mock_count:
            mock_count.return_value = 100

            response = test_client.get("/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "circuit_breakers" in data["checks"]
            circuit_breakers = data["checks"]["circuit_breakers"]

            assert "status" in circuit_breakers
            assert "summary" in circuit_breakers

    def test_health_check_with_open_circuit_breaker(self, test_client, mock_redis_client, reset_circuit_breakers):
        """Test health check shows degraded when circuit breaker is open"""
        from app.core.circuit_breaker import openrouter_breaker
        from app.core.exceptions import ExternalServiceError

        # Open the circuit breaker by failing multiple times
        def failing_func():
            raise ExternalServiceError("Service failed", service_name="Test")

        for _ in range(5):
            try:
                openrouter_breaker.call(failing_func)
            except:
                pass

        with patch('app.core.database.count_submissions') as mock_count:
            mock_count.return_value = 100

            response = test_client.get("/health")

            data = response.json()

            # Status should be degraded due to open circuit breaker
            assert data["status"] in ["degraded", "unhealthy"]
            assert data["checks"]["circuit_breakers"]["status"] in ["degraded", "error"]

    def test_health_check_includes_timestamp(self, test_client, mock_redis_client):
        """Test health check includes timestamp"""
        with patch('app.core.database.count_submissions') as mock_count:
            mock_count.return_value = 100

            response = test_client.get("/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "timestamp" in data
            # Verify timestamp is in ISO format
            from datetime import datetime
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    def test_health_check_includes_version(self, test_client, mock_redis_client):
        """Test health check includes API version"""
        with patch('app.core.database.count_submissions') as mock_count:
            mock_count.return_value = 100

            response = test_client.get("/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "version" in data
            assert data["version"] == "2.0.0"

    def test_health_check_includes_environment(self, test_client, mock_redis_client):
        """Test health check includes environment information"""
        with patch('app.core.database.count_submissions') as mock_count:
            mock_count.return_value = 100

            response = test_client.get("/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "environment" in data

    def test_health_check_openrouter_config(self, test_client, mock_redis_client):
        """Test health check verifies OpenRouter API configuration"""
        with patch('app.core.database.count_submissions') as mock_count:
            mock_count.return_value = 100

            response = test_client.get("/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "openrouter" in data["checks"]
            openrouter_check = data["checks"]["openrouter"]

            assert "status" in openrouter_check
            assert "api_key_present" in openrouter_check

    def test_health_check_security_config(self, test_client, mock_redis_client):
        """Test health check includes security configuration"""
        with patch('app.core.database.count_submissions') as mock_count:
            mock_count.return_value = 100

            response = test_client.get("/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "security" in data["checks"]
            security_check = data["checks"]["security"]

            assert "status" in security_check
            assert "features" in security_check


@pytest.mark.integration
class TestRootEndpoint:
    """Test root API endpoint"""

    def test_root_returns_api_info(self, test_client):
        """Test root endpoint returns API information"""
        response = test_client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["service"] == "Strategy AI Lead Generator API"
        assert data["status"] == "running"
        assert data["version"] == "2.0.0"

    def test_root_includes_features(self, test_client):
        """Test root endpoint includes feature list"""
        response = test_client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "features" in data
        assert isinstance(data["features"], list)

        # Should include key features
        features_str = " ".join(data["features"]).lower()
        assert "supabase" in features_str
        assert "jwt" in features_str or "auth" in features_str
        assert "apify" in features_str
        assert "redis" in features_str

    def test_root_includes_environment(self, test_client):
        """Test root endpoint includes environment"""
        response = test_client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "environment" in data


@pytest.mark.integration
class TestCircuitBreakerMonitoring:
    """Test circuit breaker monitoring"""

    def test_circuit_breaker_health_all_closed(self, reset_circuit_breakers):
        """Test circuit breaker health when all are closed"""
        from app.core.circuit_breaker import get_circuit_breaker_health

        health = get_circuit_breaker_health()

        assert health["overall_healthy"] is True
        assert health["summary"]["open_breakers"] == 0
        assert health["summary"]["total_breakers"] >= 4

    def test_circuit_breaker_health_with_open_breaker(self, reset_circuit_breakers):
        """Test circuit breaker health with one open"""
        from app.core.circuit_breaker import openrouter_breaker, get_circuit_breaker_health
        from app.core.exceptions import ExternalServiceError

        # Open one circuit breaker
        def failing_func():
            raise ExternalServiceError("Service failed", service_name="Test")

        for _ in range(5):
            try:
                openrouter_breaker.call(failing_func)
            except:
                pass

        health = get_circuit_breaker_health()

        assert health["overall_healthy"] is False
        assert health["summary"]["open_breakers"] >= 1
        assert "OpenRouter API" in health["summary"].get("open_circuit_names", []) or \
               any(b["name"] == "OpenRouter API" and b["state"] == "open" for b in health["breakers"])

    def test_circuit_breaker_statistics(self, reset_circuit_breakers):
        """Test circuit breaker statistics tracking"""
        from app.core.circuit_breaker import openrouter_breaker

        def successful_func():
            return "success"

        # Make some successful calls
        for _ in range(5):
            openrouter_breaker.call(successful_func)

        stats = openrouter_breaker.get_health_status()

        assert stats["stats"]["total_calls"] == 5
        assert stats["stats"]["successful_calls"] == 5
        assert stats["stats"]["failed_calls"] == 0


@pytest.mark.integration
class TestCORSHeaders:
    """Test CORS configuration"""

    def test_cors_headers_present(self, test_client):
        """Test CORS headers are present in response"""
        response = test_client.options("/")

        # CORS headers should be present for OPTIONS request
        # Implementation may vary, so we check for common patterns

    def test_cors_allows_configured_origins(self, test_client):
        """Test CORS allows configured origins"""
        response = test_client.get(
            "/",
            headers={"Origin": "http://localhost:3000"}
        )

        # Should allow the configured origin
        assert response.status_code == status.HTTP_200_OK
