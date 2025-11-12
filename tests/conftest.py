"""
Pytest Configuration and Fixtures for Strategy AI Backend Tests
Provides common fixtures for testing API endpoints, services, and integrations
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any, List
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import json

# Set up environment variables BEFORE importing app
# This prevents errors when modules try to read env vars on import
os.environ.setdefault("OPENROUTER_API_KEY", "test-key-123")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-supabase-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-supabase-service-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-supabase-anon-key")
os.environ.setdefault("UPSTASH_REDIS_URL", "https://test.upstash.io")  # Match Settings field name
os.environ.setdefault("UPSTASH_REDIS_TOKEN", "test-redis-token")  # Match Settings field name
os.environ.setdefault("APIFY_API_TOKEN", "test-apify-token")
os.environ.setdefault("PERPLEXITY_API_KEY", "test-perplexity-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-testing-only")  # Match Settings field name
os.environ.setdefault("CLEARBIT_API_KEY", "test-clearbit-key")
os.environ.setdefault("GOOGLE_PLACES_API_KEY", "test-google-places-key")
os.environ.setdefault("PROXYCURL_API_KEY", "test-proxycurl-key")

from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import the FastAPI app (after environment variables are set)
from app.main import app
from app.core.config import get_settings


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line("markers", "integration: Integration tests for API endpoints")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")
    config.addinivalue_line("markers", "external: Tests that require external services")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# TEST CLIENT FIXTURES
# ============================================================================

@pytest.fixture
def test_client() -> TestClient:
    """
    Synchronous test client for FastAPI

    Usage:
        def test_endpoint(test_client):
            response = test_client.get("/")
            assert response.status_code == 200
    """
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Asynchronous test client for FastAPI

    Usage:
        async def test_endpoint(async_client):
            response = await async_client.get("/")
            assert response.status_code == 200
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ============================================================================
# MOCK EXTERNAL SERVICES
# ============================================================================

@pytest.fixture
def mock_openrouter_api():
    """
    Mock OpenRouter API responses

    Returns a mock that can be configured for different test scenarios
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "diagnostico_estrategico": {
                        "forças": ["Test strength"],
                        "fraquezas": ["Test weakness"],
                        "oportunidades": ["Test opportunity"],
                        "ameaças": ["Test threat"]
                    },
                    "analise_mercado": {
                        "político": "Test political",
                        "econômico": "Test economic",
                        "social": "Test social",
                        "tecnológico": "Test tech",
                        "ambiental": "Test environmental",
                        "legal": "Test legal"
                    },
                    "oportunidades_identificadas": ["Test opportunity 1"],
                    "recomendacoes_prioritarias": ["Test recommendation 1"],
                    "proposta_okrs": [{
                        "objetivo": "Test objective",
                        "resultados_chave": ["Test KR 1"]
                    }]
                })
            }
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 200
        }
    }

    with patch('httpx.AsyncClient.post', return_value=mock_response):
        yield mock_response


@pytest.fixture
def mock_apify_client():
    """
    Mock Apify client for web scraping

    Returns mock data that simulates Apify scraper results
    """
    mock_data = {
        "company_info": {
            "name": "Test Company",
            "description": "A test company for testing purposes",
            "industry": "Technology",
            "website": "https://testcompany.com"
        },
        "linkedin_data": {
            "employees": 150,
            "founded": 2020,
            "specialties": ["AI", "Machine Learning", "Testing"]
        },
        "competitors": [
            {"name": "Competitor 1", "description": "First competitor"},
            {"name": "Competitor 2", "description": "Second competitor"}
        ]
    }

    with patch('app.services.data.apify_client.ApifyClient') as mock:
        instance = mock.return_value
        instance.get_company_data.return_value = mock_data
        instance.scrape_website.return_value = {"content": "Test website content"}
        yield instance


@pytest.fixture
def mock_perplexity_api():
    """
    Mock Perplexity API for research queries

    Returns mock research data
    """
    mock_response = {
        "answer": "Test research answer about the company and industry trends.",
        "sources": [
            "https://example.com/source1",
            "https://example.com/source2"
        ]
    }

    with patch('app.services.data.perplexity.query_perplexity', return_value=mock_response):
        yield mock_response


@pytest.fixture
def mock_supabase_client():
    """
    Mock Supabase client for database operations

    Returns a mock client with common database operations
    """
    mock_client = Mock()

    # Mock table operations
    mock_table = Mock()
    mock_client.table.return_value = mock_table

    # Mock query operations
    mock_query = Mock()
    mock_table.select.return_value = mock_query
    mock_table.insert.return_value = mock_query
    mock_table.update.return_value = mock_query
    mock_table.delete.return_value = mock_query

    # Chain operations
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.lte.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.order.return_value = mock_query

    # Mock execute
    mock_result = Mock()
    mock_result.data = []
    mock_query.execute.return_value = mock_result

    with patch('app.core.supabase.supabase_service', mock_client):
        yield mock_client


@pytest.fixture
def mock_redis_client():
    """
    Mock Redis client for caching and rate limiting

    Returns a mock Redis client
    """
    mock_client = Mock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.delete.return_value = 1
    mock_client.incr.return_value = 1
    mock_client.expire.return_value = True

    with patch('app.core.security.rate_limiter.get_redis_client', return_value=mock_client):
        yield mock_client


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================

@pytest.fixture
def mock_jwt_token() -> str:
    """
    Generate a mock JWT token for testing authenticated endpoints

    Usage:
        def test_protected_endpoint(test_client, mock_jwt_token):
            response = test_client.get(
                "/api/admin/submissions",
                headers={"Authorization": f"Bearer {mock_jwt_token}"}
            )
    """
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxOTAwMDAwMDAwfQ.test_signature"


@pytest.fixture
def mock_user_data() -> Dict[str, Any]:
    """
    Mock user data for authentication tests

    Returns a dictionary representing an authenticated user
    """
    return {
        "id": "test-user-id-123",
        "email": "test@example.com",
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def mock_authenticated_request(mock_user_data):
    """
    Mock authenticated request for dependency injection

    Bypasses actual JWT validation for testing
    """
    from app.routes.auth import RequireAuth

    async def override_auth():
        return mock_user_data

    app.dependency_overrides[RequireAuth] = override_auth
    yield mock_user_data
    app.dependency_overrides.clear()


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_submission_data() -> Dict[str, Any]:
    """
    Sample submission data for testing form submissions

    Returns valid submission data matching the SubmissionCreate schema
    """
    return {
        "name": "John Doe",
        "email": "john@testcompany.com",
        "company": "Test Company Inc",
        "website": "https://testcompany.com",
        "linkedin_company": "https://linkedin.com/company/testcompany",
        "linkedin_founder": "https://linkedin.com/in/johndoe",
        "industry": "Tecnologia",
        "challenge": "Expandir presença no mercado B2B"
    }


@pytest.fixture
def sample_analysis_report() -> Dict[str, Any]:
    """
    Sample analysis report data for testing report generation

    Returns a complete analysis report matching the expected JSON structure
    """
    return {
        "diagnostico_estrategico": {
            "forças": [
                "Equipe técnica experiente",
                "Produto inovador",
                "Base de clientes fiéis"
            ],
            "fraquezas": [
                "Orçamento de marketing limitado",
                "Processos operacionais não escaláveis",
                "Dependência de poucos clientes"
            ],
            "oportunidades": [
                "Crescimento do mercado B2B SaaS",
                "Parcerias estratégicas com integradores",
                "Expansão para novos verticais"
            ],
            "ameaças": [
                "Concorrentes internacionais entrando no mercado",
                "Mudanças regulatórias em proteção de dados",
                "Volatilidade econômica"
            ]
        },
        "analise_mercado": {
            "político": "Ambiente regulatório favorável para tecnologia",
            "econômico": "Crescimento de 15% ao ano no setor de tecnologia",
            "social": "Aumento da digitalização empresarial",
            "tecnológico": "Adoção de IA e automação em alta",
            "ambiental": "Pressão por soluções sustentáveis",
            "legal": "Conformidade com LGPD obrigatória"
        },
        "oportunidades_identificadas": [
            "Lançar programa de parcerias com integradores regionais",
            "Desenvolver módulo específico para setor de varejo",
            "Implementar programa de marketing de conteúdo B2B"
        ],
        "recomendacoes_prioritarias": [
            "Investir em automação de processos operacionais (3 meses)",
            "Contratar especialista em marketing B2B (imediato)",
            "Desenvolver estratégia de diversificação de clientes (6 meses)"
        ],
        "proposta_okrs": [
            {
                "objetivo": "Expandir base de clientes B2B em 200%",
                "resultados_chave": [
                    "Assinar contratos com 50 novos clientes B2B",
                    "Alcançar R$ 500k MRR até Q4",
                    "Reduzir custo de aquisição de cliente em 30%"
                ]
            },
            {
                "objetivo": "Tornar-se referência em automação empresarial",
                "resultados_chave": [
                    "Publicar 20 cases de sucesso",
                    "Alcançar 100k visitantes mensais no blog",
                    "Ser mencionado em 5 veículos de mídia especializados"
                ]
            }
        ],
        "_metadata": {
            "version": "2.0",
            "generated_at": datetime.utcnow().isoformat(),
            "total_cost": 0.15,
            "processing_time": 45.2
        }
    }


@pytest.fixture
def sample_submission_record(sample_submission_data, sample_analysis_report) -> Dict[str, Any]:
    """
    Sample submission database record for testing

    Returns a complete submission record as it would appear in the database
    """
    return {
        "id": 123,
        "name": sample_submission_data["name"],
        "email": sample_submission_data["email"],
        "company": sample_submission_data["company"],
        "website": sample_submission_data["website"],
        "linkedin_company": sample_submission_data["linkedin_company"],
        "linkedin_founder": sample_submission_data["linkedin_founder"],
        "industry": sample_submission_data["industry"],
        "challenge": sample_submission_data["challenge"],
        "status": "completed",
        "report_json": json.dumps(sample_analysis_report),
        "error_message": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# CIRCUIT BREAKER FIXTURES
# ============================================================================

@pytest.fixture
def reset_circuit_breakers():
    """
    Reset all circuit breakers to closed state before each test

    Ensures tests start with clean circuit breaker state
    """
    from app.core.circuit_breaker import (
        openrouter_breaker,
        apify_breaker,
        perplexity_breaker,
        supabase_breaker
    )

    breakers = [openrouter_breaker, apify_breaker, perplexity_breaker, supabase_breaker]

    for breaker in breakers:
        breaker.reset()

    yield

    # Reset again after test
    for breaker in breakers:
        breaker.reset()


# ============================================================================
# COST TRACKING FIXTURES
# ============================================================================

@pytest.fixture
def mock_cost_tracker():
    """
    Mock cost tracker for testing cost calculations

    Returns a mock CostTracker instance
    """
    from app.utils.validation import CostTracker

    tracker = CostTracker()
    # Pre-populate with some test data
    tracker.log_usage("test_stage", "test_model", 100, 200)

    return tracker


# ============================================================================
# UTILITY FUNCTIONS FOR TESTS
# ============================================================================

@pytest.fixture
def assert_valid_json():
    """
    Helper function to assert that a string is valid JSON

    Usage:
        def test_json_output(assert_valid_json):
            result = '{"key": "value"}'
            assert_valid_json(result)
    """
    def _assert_valid_json(json_string: str):
        try:
            json.loads(json_string)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON: {e}")

    return _assert_valid_json


@pytest.fixture
def assert_valid_report_structure(sample_analysis_report):
    """
    Helper function to assert that a report has the expected structure

    Usage:
        def test_report_generation(assert_valid_report_structure):
            report = generate_report()
            assert_valid_report_structure(report)
    """
    def _assert_valid_structure(report: Dict[str, Any]):
        required_keys = [
            "diagnostico_estrategico",
            "analise_mercado",
            "oportunidades_identificadas",
            "recomendacoes_prioritarias",
            "proposta_okrs"
        ]

        for key in required_keys:
            assert key in report, f"Missing required key: {key}"

        # Check SWOT structure
        swot = report["diagnostico_estrategico"]
        assert all(k in swot for k in ["forças", "fraquezas", "oportunidades", "ameaças"])

        # Check PESTEL structure
        pestel = report["analise_mercado"]
        assert all(k in pestel for k in ["político", "econômico", "social", "tecnológico", "ambiental", "legal"])

        # Check OKRs structure
        assert isinstance(report["proposta_okrs"], list)
        if report["proposta_okrs"]:
            okr = report["proposta_okrs"][0]
            assert "objetivo" in okr
            assert "resultados_chave" in okr

    return _assert_valid_structure


# ============================================================================
# ENVIRONMENT FIXTURES
# ============================================================================

@pytest.fixture
def test_settings():
    """
    Override settings for testing

    Returns test-specific configuration
    """
    settings = get_settings()
    # Override settings for testing
    settings.environment = "testing"
    settings.allowed_origins = ["http://localhost:3000", "http://test"]

    return settings


@pytest.fixture
def mock_env_vars(monkeypatch):
    """
    Mock environment variables for testing

    Usage:
        def test_with_env(mock_env_vars):
            # Environment variables are set
            pass
    """
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-supabase-key")
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://test.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "test-redis-token")
    monkeypatch.setenv("APIFY_API_TOKEN", "test-apify-token")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-perplexity-key")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    # Enrichment API keys
    monkeypatch.setenv("CLEARBIT_API_KEY", "test-clearbit-key")
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "test-google-places-key")
    monkeypatch.setenv("PROXYCURL_API_KEY", "test-proxycurl-key")

    yield


# ============================================================================
# ENRICHMENT FIXTURES (IMENSIAH)
# ============================================================================

@pytest.fixture
def sample_enrichment_submission() -> Dict[str, Any]:
    """
    Sample enrichment submission data

    Returns valid enrichment submission matching the API schema
    """
    return {
        "email": "contato@techstart.com.br",
        "company_website": "https://techstart.com.br"
    }


@pytest.fixture
def sample_quick_enrichment() -> Dict[str, Any]:
    """
    Sample quick enrichment data (2-3s response)

    Returns enrichment data with basic fields from free sources
    """
    return {
        "website": "https://techstart.com.br",
        "domain": "techstart.com.br",
        "company_name": "TechStart Innovations",
        "description": "Innovative tech solutions for startups",
        "location": "São Paulo, SP, Brazil",
        "tech_stack": ["React", "Next.js", "Vercel"],
        "logo_url": "https://techstart.com/logo.png",
        "social_media": {
            "twitter": "https://twitter.com/techstart",
            "linkedin": "https://linkedin.com/company/techstart"
        },
        "ip_timezone": "America/Sao_Paulo",
        "source_attribution": {
            "company_name": "metadata",
            "location": "ip_api"
        },
        "sources_called": ["metadata", "ip_api"],
        "completeness_score": 35.0,
        "confidence_score": 65.0,
        "data_quality_tier": "moderate",
        "total_cost_usd": 0.0,
        "quick_duration_ms": 2150,
        "quick_completed_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_deep_enrichment() -> Dict[str, Any]:
    """
    Sample deep enrichment data (30s+ response)

    Returns comprehensive enrichment data from all 6 sources
    """
    return {
        "website": "https://techstart.com.br",
        "domain": "techstart.com.br",
        "company_name": "TechStart Innovations",
        "cnpj": "12.345.678/0001-99",
        "legal_name": "TechStart Inovações Ltda",
        "employee_count": "25-50",
        "annual_revenue": "$500K-1M",
        "industry": "Software",
        "founded_year": 2019,
        "address": "Av. Paulista, 1000 - São Paulo, SP",
        "phone": "+55 11 9999-8888",
        "rating": 4.7,
        "reviews_count": 124,
        "linkedin_url": "https://linkedin.com/company/techstart",
        "linkedin_followers": 1247,
        "linkedin_description": "Full company description",
        "specialties": ["SaaS", "Cloud Computing", "AI/ML"],
        "source_attribution": {
            "company_name": "metadata",
            "cnpj": "receita_ws",
            "employee_count": "clearbit",
            "rating": "google_places",
            "linkedin_followers": "proxycurl"
        },
        "sources_called": [
            "metadata",
            "ip_api",
            "receita_ws",
            "clearbit",
            "google_places",
            "proxycurl"
        ],
        "completeness_score": 94.0,
        "confidence_score": 89.0,
        "data_quality_tier": "excellent",
        "total_cost_usd": 0.15,
        "quick_duration_ms": 2150,
        "deep_duration_ms": 31400,
        "deep_completed_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_enrichment_audit_logs() -> List[Dict[str, Any]]:
    """
    Sample audit logs for enrichment

    Returns complete audit trail showing all API calls made
    """
    return [
        {
            "id": 1,
            "enrichment_id": 123,
            "source_name": "metadata",
            "request_data": {"domain": "techstart.com.br"},
            "response_data": {"company_name": "TechStart Innovations"},
            "success": True,
            "cost_usd": 0.0,
            "duration_ms": 500,
            "circuit_breaker_state": "closed",
            "cached": False,
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": 2,
            "enrichment_id": 123,
            "source_name": "clearbit",
            "request_data": {"domain": "techstart.com.br"},
            "response_data": {"employee_count": "25-50"},
            "success": True,
            "cost_usd": 0.10,
            "duration_ms": 1500,
            "circuit_breaker_state": "closed",
            "cached": False,
            "created_at": datetime.utcnow().isoformat()
        }
    ]
