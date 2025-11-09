"""
Unit Tests for Enrichment Data Sources

Tests all 6 data source integrations:
- MetadataSource (free website scraping)
- IpApiSource (free IP geolocation)
- ReceitaWSSource (free Brazilian CNPJ lookup)
- ClearbitSource (paid company data)
- GooglePlacesSource (paid location verification)
- ProxycurlSource (paid LinkedIn data)
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import httpx

from app.services.enrichment.sources.base import EnrichmentSource, SourceResult
from app.services.enrichment.sources.metadata import MetadataSource
from app.services.enrichment.sources.ip_api import IpApiSource
from app.services.enrichment.sources.receita_ws import ReceitaWSSource
from app.services.enrichment.sources.clearbit import ClearbitSource
from app.services.enrichment.sources.google_places import GooglePlacesSource
from app.services.enrichment.sources.proxycurl import ProxycurlSource


@pytest.mark.unit
@pytest.mark.asyncio
class TestMetadataSource:
    """Test MetadataSource (free website metadata scraping)"""

    async def test_successful_metadata_extraction(self):
        """Test successful metadata extraction from website"""
        source = MetadataSource()

        # Mock HTML response
        html_content = """
        <html>
            <head>
                <title>TechStart Innovations - Innovative Solutions</title>
                <meta name="description" content="We provide innovative tech solutions for startups">
                <meta property="og:image" content="https://techstart.com/logo.png">
            </head>
            <body>
                <a href="https://twitter.com/techstart">Twitter</a>
                <a href="https://linkedin.com/company/techstart">LinkedIn</a>
                <script src="/_next/static/main.js"></script>
            </body>
        </html>
        """

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html_content
        mock_response.headers = {"content-type": "text/html"}

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich("techstart.com.br")

        assert result.success is True
        assert result.data["company_name"] == "TechStart Innovations"
        assert "innovative tech solutions" in result.data["description"].lower()
        assert result.data["logo_url"] == "https://techstart.com/logo.png"
        assert "Next.js" in result.data["tech_stack"]

    async def test_tech_stack_detection(self):
        """Test technology stack detection"""
        source = MetadataSource()

        html_with_tech = """
        <html>
            <script src="react.js"></script>
            <script src="/_next/static/main.js"></script>
            <div data-react-root></div>
        </html>
        """

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html_with_tech

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich("test.com")

        assert "React" in result.data["tech_stack"]
        assert "Next.js" in result.data["tech_stack"]

    async def test_social_media_extraction(self):
        """Test social media link extraction"""
        source = MetadataSource()

        html_with_social = """
        <html>
            <a href="https://twitter.com/company">Twitter</a>
            <a href="https://facebook.com/company">Facebook</a>
            <a href="https://linkedin.com/company/test">LinkedIn</a>
        </html>
        """

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html_with_social

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich("test.com")

        social = result.data["social_media"]
        assert social["twitter"] == "https://twitter.com/company"
        assert social["facebook"] == "https://facebook.com/company"
        assert social["linkedin"] == "https://linkedin.com/company/test"

    async def test_timeout_handling(self):
        """Test timeout error handling"""
        source = MetadataSource()

        with patch('httpx.AsyncClient.get', side_effect=httpx.TimeoutException("Timeout")):
            result = await source.enrich("slow-website.com")

        assert result.success is False
        assert result.error_type == "timeout"

    async def test_http_error_handling(self):
        """Test HTTP error handling (404, 500, etc.)"""
        source = MetadataSource()

        mock_response = Mock()
        mock_response.status_code = 404

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich("nonexistent.com")

        assert result.success is False
        assert result.error_type == "http_404"


@pytest.mark.unit
@pytest.mark.asyncio
class TestIpApiSource:
    """Test IpApiSource (free IP geolocation)"""

    async def test_successful_ip_geolocation(self):
        """Test successful IP geolocation"""
        source = IpApiSource()

        # Mock IP API response
        mock_ip_response = {
            "status": "success",
            "country": "Brazil",
            "countryCode": "BR",
            "region": "SP",
            "regionName": "São Paulo",
            "city": "São Paulo",
            "zip": "01000",
            "lat": -23.5505,
            "lon": -46.6333,
            "timezone": "America/Sao_Paulo",
            "isp": "Example ISP"
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_ip_response

        with patch('socket.gethostbyname', return_value="200.200.200.200"):
            with patch('httpx.AsyncClient.get', return_value=mock_response):
                result = await source.enrich("techstart.com.br")

        assert result.success is True
        assert "São Paulo" in result.data["location"]
        assert "Brazil" in result.data["location"]
        assert result.data["ip_timezone"] == "America/Sao_Paulo"

    async def test_dns_resolution_failure(self):
        """Test DNS resolution failure"""
        source = IpApiSource()

        with patch('socket.gethostbyname', side_effect=OSError("DNS lookup failed")):
            result = await source.enrich("invalid-domain.com")

        assert result.success is False
        assert result.error_type == "dns_error"


@pytest.mark.unit
@pytest.mark.asyncio
class TestReceitaWSSource:
    """Test ReceitaWSSource (free Brazilian CNPJ lookup)"""

    async def test_successful_cnpj_lookup(self):
        """Test successful CNPJ lookup"""
        source = ReceitaWSSource()

        # Mock ReceitaWS response
        mock_receita_response = {
            "status": "OK",
            "cnpj": "12.345.678/0001-99",
            "nome": "TechStart Inovações Ltda",
            "fantasia": "TechStart",
            "atividade_principal": [
                {"code": "62.01-5-00", "text": "Desenvolvimento de software"}
            ],
            "logradouro": "Av. Paulista",
            "numero": "1000",
            "municipio": "São Paulo",
            "uf": "SP",
            "cep": "01310-100"
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_receita_response

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich(
                "techstart.com.br",
                company_name="TechStart Inovações"
            )

        assert result.success is True
        assert result.data["cnpj"] == "12.345.678/0001-99"
        assert result.data["legal_name"] == "TechStart Inovações Ltda"
        assert "São Paulo - SP" in result.data["address"]

    async def test_cnpj_not_found(self):
        """Test CNPJ not found in ReceitaWS"""
        source = ReceitaWSSource()

        mock_response = Mock()
        mock_response.status_code = 404

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich("test.com", company_name="Unknown Company")

        assert result.success is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestClearbitSource:
    """Test ClearbitSource (paid company enrichment)"""

    async def test_successful_company_enrichment(self):
        """Test successful Clearbit company enrichment"""
        source = ClearbitSource(api_key="test-key")

        # Mock Clearbit response
        mock_clearbit_response = {
            "id": "company-123",
            "name": "TechStart Innovations",
            "legalName": "TechStart Innovations Ltd",
            "domain": "techstart.com",
            "metrics": {
                "employeesRange": "25-50",
                "annualRevenue": 1000000
            },
            "category": {
                "industry": "Software",
                "sector": "Technology"
            },
            "foundedYear": 2019,
            "description": "Innovative tech solutions for startups",
            "tech": ["react", "aws", "postgresql"]
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_clearbit_response

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich("techstart.com")

        assert result.success is True
        assert result.data["company_name"] == "TechStart Innovations"
        assert result.data["employee_count"] == "25-50"
        assert result.data["industry"] == "Software"
        assert result.data["founded_year"] == 2019

    async def test_clearbit_rate_limit(self):
        """Test Clearbit rate limit handling"""
        source = ClearbitSource(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 429  # Rate limit

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich("test.com")

        assert result.success is False
        assert result.error_type == "rate_limit"

    async def test_clearbit_invalid_api_key(self):
        """Test Clearbit invalid API key"""
        source = ClearbitSource(api_key="invalid-key")

        mock_response = Mock()
        mock_response.status_code = 401  # Unauthorized

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich("test.com")

        assert result.success is False
        assert result.error_type == "auth_error"


@pytest.mark.unit
@pytest.mark.asyncio
class TestGooglePlacesSource:
    """Test GooglePlacesSource (paid location verification)"""

    async def test_successful_place_lookup(self):
        """Test successful Google Places lookup"""
        source = GooglePlacesSource(api_key="test-key")

        # Mock Find Place response
        mock_find_response = {
            "status": "OK",
            "candidates": [
                {"place_id": "ChIJtest123"}
            ]
        }

        # Mock Place Details response
        mock_details_response = {
            "status": "OK",
            "result": {
                "name": "TechStart Innovations",
                "formatted_address": "Av. Paulista, 1000 - São Paulo, SP",
                "international_phone_number": "+55 11 9999-8888",
                "rating": 4.7,
                "user_ratings_total": 124,
                "geometry": {
                    "location": {
                        "lat": -23.5505,
                        "lng": -46.6333
                    }
                }
            }
        }

        mock_find = Mock()
        mock_find.status_code = 200
        mock_find.json.return_value = mock_find_response

        mock_details = Mock()
        mock_details.status_code = 200
        mock_details.json.return_value = mock_details_response

        with patch('httpx.AsyncClient.get', side_effect=[mock_find, mock_details]):
            result = await source.enrich(
                "techstart.com",
                company_name="TechStart",
                city="São Paulo"
            )

        assert result.success is True
        assert result.data["address"] == "Av. Paulista, 1000 - São Paulo, SP"
        assert result.data["phone"] == "+55 11 9999-8888"
        assert result.data["rating"] == 4.7
        assert result.data["reviews_count"] == 124

    async def test_place_not_found(self):
        """Test place not found in Google Places"""
        source = GooglePlacesSource(api_key="test-key")

        mock_response = {
            "status": "ZERO_RESULTS",
            "candidates": []
        }

        mock_find = Mock()
        mock_find.status_code = 200
        mock_find.json.return_value = mock_response

        with patch('httpx.AsyncClient.get', return_value=mock_find):
            result = await source.enrich("test.com", company_name="Unknown")

        assert result.success is False
        assert result.error_type == "not_found"


@pytest.mark.unit
@pytest.mark.asyncio
class TestProxycurlSource:
    """Test ProxycurlSource (paid LinkedIn data)"""

    async def test_successful_linkedin_lookup(self):
        """Test successful LinkedIn company lookup"""
        source = ProxycurlSource(api_key="test-key")

        # Mock Proxycurl response
        mock_proxycurl_response = {
            "name": "TechStart Innovations",
            "description": "Innovative tech solutions for startups",
            "follower_count": 1247,
            "website": "https://techstart.com",
            "company_size": [25, 50],
            "specialities": "SaaS, Cloud Computing, AI/ML, Data Analytics",
            "universal_name_id": "techstart-innovations"
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_proxycurl_response

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich(
                "techstart.com",
                company_name="TechStart"
            )

        assert result.success is True
        assert result.data["linkedin_followers"] == 1247
        assert "SaaS" in result.data["specialties"]
        assert "Cloud Computing" in result.data["specialties"]

    async def test_linkedin_url_not_found(self):
        """Test LinkedIn URL resolution failure"""
        source = ProxycurlSource(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 404

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich("test.com", company_name="Unknown")

        assert result.success is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestSourceCircuitBreaker:
    """Test circuit breaker integration in sources"""

    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after consecutive failures"""
        source = MetadataSource()

        # Cause 5 failures to trip circuit breaker
        with patch('httpx.AsyncClient.get', side_effect=Exception("Connection error")):
            for _ in range(5):
                result = await source.enrich_with_monitoring("test.com")
                assert result.success is False

        # Circuit breaker should now be open
        assert source.circuit_breaker.state == "open"

        # Next call should fail immediately without API call
        result = await source.enrich_with_monitoring("test.com")
        assert result.success is False
        assert result.error_type == "circuit_breaker"

    async def test_circuit_breaker_resets_after_success(self):
        """Test circuit breaker resets after successful calls"""
        source = MetadataSource()

        # Reset circuit breaker to closed
        source.circuit_breaker.reset()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><title>Test</title></html>"

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich_with_monitoring("test.com")

        assert result.success is True
        assert source.circuit_breaker.state == "closed"


@pytest.mark.unit
class TestSourceCostTracking:
    """Test cost tracking in data sources"""

    def test_free_source_cost(self):
        """Test free sources have zero cost"""
        metadata = MetadataSource()
        ip_api = IpApiSource()
        receita = ReceitaWSSource()

        assert metadata.cost_per_call == 0.0
        assert ip_api.cost_per_call == 0.0
        assert receita.cost_per_call == 0.0

    def test_paid_source_costs(self):
        """Test paid sources have correct costs"""
        clearbit = ClearbitSource(api_key="test")
        google_places = GooglePlacesSource(api_key="test")
        proxycurl = ProxycurlSource(api_key="test")

        assert clearbit.cost_per_call == 0.10
        assert google_places.cost_per_call == 0.02
        assert proxycurl.cost_per_call == 0.03


@pytest.mark.unit
class TestSourceResultModel:
    """Test SourceResult data model"""

    def test_successful_result_creation(self):
        """Test creating successful result"""
        result = SourceResult(
            success=True,
            data={"company_name": "Test Company"},
            source_name="test_source",
            duration_ms=150,
            cost_usd=0.10
        )

        assert result.success is True
        assert result.data["company_name"] == "Test Company"
        assert result.duration_ms == 150
        assert result.cost_usd == 0.10

    def test_failed_result_creation(self):
        """Test creating failed result"""
        result = SourceResult(
            success=False,
            error_type="timeout",
            error_message="Request timed out after 10s",
            source_name="test_source"
        )

        assert result.success is False
        assert result.error_type == "timeout"
        assert result.data == {}


@pytest.mark.unit
@pytest.mark.asyncio
class TestSourceRetryLogic:
    """Test retry logic for transient failures"""

    async def test_retry_on_timeout(self):
        """Test automatic retry on timeout"""
        source = MetadataSource()

        # First call times out, second succeeds
        mock_success = Mock()
        mock_success.status_code = 200
        mock_success.text = "<html><title>Test</title></html>"

        with patch('httpx.AsyncClient.get', side_effect=[
            httpx.TimeoutException("Timeout"),
            mock_success
        ]):
            # Note: Current implementation doesn't have retry logic
            # This test documents expected behavior
            result = await source.enrich("test.com")
            # First attempt fails
            assert result.success is False

            # Would need to call again manually
            result2 = await source.enrich("test.com")
            assert result2.success is True


@pytest.mark.unit
@pytest.mark.asyncio
class TestSourceDataNormalization:
    """Test data normalization across sources"""

    async def test_cnpj_formatting(self):
        """Test CNPJ is formatted consistently"""
        source = ReceitaWSSource()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "cnpj": "12345678000199",  # Unformatted
            "nome": "Test Company"
        }

        with patch('httpx.AsyncClient.get', return_value=mock_response):
            result = await source.enrich("test.com", company_name="Test")

        # Should be formatted as XX.XXX.XXX/XXXX-XX
        assert result.data["cnpj"] == "12.345.678/0001-99"

    async def test_phone_number_formatting(self):
        """Test phone numbers are formatted consistently"""
        source = GooglePlacesSource(api_key="test")

        # Mock responses
        mock_find = Mock()
        mock_find.status_code = 200
        mock_find.json.return_value = {
            "status": "OK",
            "candidates": [{"place_id": "test123"}]
        }

        mock_details = Mock()
        mock_details.status_code = 200
        mock_details.json.return_value = {
            "status": "OK",
            "result": {
                "international_phone_number": "+55 11 9999-8888"
            }
        }

        with patch('httpx.AsyncClient.get', side_effect=[mock_find, mock_details]):
            result = await source.enrich("test.com", company_name="Test")

        # Phone should include country code
        assert result.data["phone"].startswith("+55")
