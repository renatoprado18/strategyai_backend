"""
Enhanced enrichment tests for the 3-layer progressive enrichment system
Tests Layer 1 (metadata), Layer 2 (external APIs), and Layer 3 (AI inference)
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import asyncio

from app.services.enrichment.progressive_orchestrator import ProgressiveOrchestrator
from app.services.enrichment.layer1_metadata import MetadataExtractor
from app.services.enrichment.layer2_sources import ExternalSourceEnricher
from app.services.enrichment.layer3_ai import AIInferenceEngine
from app.models.schemas import EnrichmentRequest, EnrichmentResponse
from tests.fixtures.enrichment_data import (
    SAMPLE_COMPANIES,
    SOCIAL_MEDIA_TESTS,
    PHONE_TESTS,
    URL_TESTS,
    CONFIDENCE_THRESHOLDS
)


class TestLayer1MetadataExtraction:
    """Test Layer 1: Metadata extraction from website"""

    @pytest.fixture
    def metadata_extractor(self):
        return MetadataExtractor()

    @pytest.mark.asyncio
    async def test_metadata_extraction_basic(self, metadata_extractor):
        """Test basic metadata extraction from HTML"""
        url = "https://example.com"
        html_content = """
        <html>
            <head>
                <title>Example Company</title>
                <meta name="description" content="We are a test company">
                <meta property="og:image" content="https://example.com/logo.png">
            </head>
            <body>
                <h1>Welcome to Example Company</h1>
            </body>
        </html>
        """

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value=html_content)
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await metadata_extractor.extract(url)

            assert result["title"] == "Example Company"
            assert "test company" in result["meta_description"].lower()
            assert result["og_image"] == "https://example.com/logo.png"

    @pytest.mark.asyncio
    async def test_social_media_detection(self, metadata_extractor):
        """Test detection of social media links in metadata"""
        url = "https://example.com"
        html_content = """
        <html>
            <body>
                <a href="https://instagram.com/example">Instagram</a>
                <a href="https://tiktok.com/@example">TikTok</a>
                <a href="https://linkedin.com/company/example">LinkedIn</a>
            </body>
        </html>
        """

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value=html_content)
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await metadata_extractor.extract(url)

            assert "instagram.com/example" in result.get("social_links", [])
            assert "tiktok.com/@example" in result.get("social_links", [])
            assert "linkedin.com/company/example" in result.get("social_links", [])

    @pytest.mark.asyncio
    async def test_metadata_extraction_timeout(self, metadata_extractor):
        """Test that metadata extraction handles timeouts gracefully"""
        url = "https://slow-website.com"

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError()

            result = await metadata_extractor.extract(url)

            # Should return partial/empty data, not raise exception
            assert isinstance(result, dict)
            assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_metadata_extraction_invalid_html(self, metadata_extractor):
        """Test handling of malformed HTML"""
        url = "https://example.com"
        html_content = "<html><title>Broken HTML"

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value=html_content)
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await metadata_extractor.extract(url)

            # Should still extract what it can
            assert isinstance(result, dict)
            assert "title" in result or "error" in result


class TestLayer2SourceSelection:
    """Test Layer 2: Intelligent source selection and data reconciliation"""

    @pytest.fixture
    def source_enricher(self):
        return ExternalSourceEnricher()

    @pytest.mark.asyncio
    async def test_brazilian_domain_uses_receitaws(self, source_enricher):
        """Test that Brazilian domains (.com.br) use ReceitaWS"""
        url = "https://example.com.br"

        with patch.object(source_enricher, '_enrich_receitaws') as mock_receitaws:
            mock_receitaws.return_value = {"company_name": "Example BR"}

            result = await source_enricher.enrich(url, {})

            mock_receitaws.assert_called_once()

    @pytest.mark.asyncio
    async def test_international_domain_uses_clearbit(self, source_enricher):
        """Test that international domains use Clearbit"""
        url = "https://example.com"

        with patch.object(source_enricher, '_enrich_clearbit') as mock_clearbit:
            mock_clearbit.return_value = {"company_name": "Example Inc"}

            result = await source_enricher.enrich(url, {})

            mock_clearbit.assert_called_once()

    @pytest.mark.asyncio
    async def test_data_reconciliation_multiple_sources(self, source_enricher):
        """Test that data from multiple sources is reconciled correctly"""
        url = "https://example.com"
        layer1_data = {"company_name": "Example", "industry": "Tech"}

        clearbit_data = {"company_name": "Example Inc", "employees": 100}

        with patch.object(source_enricher, '_enrich_clearbit') as mock_clearbit:
            mock_clearbit.return_value = clearbit_data

            result = await source_enricher.enrich(url, layer1_data)

            # Should merge both sources
            assert result["company_name"] in ["Example Inc", "Example"]
            assert result["industry"] == "Tech"  # From layer1
            assert result.get("employees") == 100  # From Clearbit

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_api_failure(self, source_enricher):
        """Test that enrichment continues even if external API fails"""
        url = "https://example.com"
        layer1_data = {"company_name": "Example", "industry": "Tech"}

        with patch.object(source_enricher, '_enrich_clearbit') as mock_clearbit:
            mock_clearbit.side_effect = Exception("API Error")

            result = await source_enricher.enrich(url, layer1_data)

            # Should fall back to Layer 1 data
            assert result["company_name"] == "Example"
            assert result["industry"] == "Tech"


class TestLayer3AIInference:
    """Test Layer 3: AI-powered inference and enhancement"""

    @pytest.fixture
    def ai_engine(self):
        return AIInferenceEngine()

    @pytest.mark.asyncio
    async def test_ai_inference_structured_output(self, ai_engine):
        """Test that AI inference returns structured, parseable output"""
        enriched_data = {
            "company_name": "Tech Startup",
            "url": "https://techstartup.com",
            "description": "We build AI solutions"
        }

        mock_ai_response = {
            "industry": "Artificial Intelligence",
            "target_market": "B2B Enterprise",
            "company_size": "11-50 employees",
            "confidence_scores": {
                "industry": 0.92,
                "target_market": 0.85,
                "company_size": 0.78
            }
        }

        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value = AsyncMock(
                choices=[AsyncMock(message={"content": str(mock_ai_response)})]
            )

            result = await ai_engine.infer(enriched_data)

            assert "industry" in result
            assert "confidence_scores" in result
            assert isinstance(result["confidence_scores"], dict)

    @pytest.mark.asyncio
    async def test_confidence_scoring(self, ai_engine):
        """Test that confidence scores are calculated correctly"""
        enriched_data = {
            "company_name": "Example Corp",
            "industry": "Technology",
            "description": "Software company"
        }

        result = await ai_engine.infer(enriched_data)

        # Check confidence scores exist and are in valid range
        assert "confidence_scores" in result
        for field, score in result["confidence_scores"].items():
            assert 0.0 <= score <= 1.0
            assert score >= CONFIDENCE_THRESHOLDS["minimum_acceptable"]

    @pytest.mark.asyncio
    async def test_ai_timeout_fallback(self, ai_engine):
        """Test that AI timeout doesn't break the pipeline"""
        enriched_data = {"company_name": "Example"}

        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.side_effect = asyncio.TimeoutError()

            result = await ai_engine.infer(enriched_data)

            # Should return enriched_data with low confidence scores
            assert result["company_name"] == "Example"
            assert "confidence_scores" in result


class TestProgressiveOrchestrator:
    """Test the orchestrator that coordinates all 3 layers"""

    @pytest.fixture
    def orchestrator(self):
        return ProgressiveOrchestrator()

    @pytest.mark.asyncio
    async def test_complete_enrichment_flow(self, orchestrator):
        """Test full 3-layer enrichment end-to-end"""
        request = EnrichmentRequest(
            url="https://example.com",
            review_cycle="monthly"
        )

        with patch.object(orchestrator.layer1, 'extract') as mock_l1, \
             patch.object(orchestrator.layer2, 'enrich') as mock_l2, \
             patch.object(orchestrator.layer3, 'infer') as mock_l3:

            mock_l1.return_value = {"company_name": "Example", "industry": "Tech"}
            mock_l2.return_value = {"company_name": "Example Inc", "industry": "Tech", "employees": 50}
            mock_l3.return_value = {
                "company_name": "Example Inc",
                "industry": "Technology",
                "employees": 50,
                "confidence_scores": {"company_name": 0.95, "industry": 0.90}
            }

            response = await orchestrator.enrich(request)

            assert isinstance(response, EnrichmentResponse)
            assert response.company_name == "Example Inc"
            assert response.industry == "Technology"
            assert hasattr(response, 'confidence_scores')

    @pytest.mark.asyncio
    async def test_enrichment_with_social_media(self, orchestrator):
        """Test enrichment properly handles social media fields"""
        request = EnrichmentRequest(
            url="https://example.com",
            instagram="@example"
        )

        response = await orchestrator.enrich(request)

        # Should convert @handle to full URL
        assert "instagram.com" in response.instagram or response.instagram == "@example"

    @pytest.mark.asyncio
    async def test_partial_enrichment_on_errors(self, orchestrator):
        """Test that partial enrichment succeeds even with layer failures"""
        request = EnrichmentRequest(url="https://example.com")

        with patch.object(orchestrator.layer1, 'extract') as mock_l1, \
             patch.object(orchestrator.layer2, 'enrich') as mock_l2, \
             patch.object(orchestrator.layer3, 'infer') as mock_l3:

            mock_l1.return_value = {"company_name": "Example"}
            mock_l2.side_effect = Exception("API Error")
            mock_l3.side_effect = Exception("AI Error")

            response = await orchestrator.enrich(request)

            # Should at least have Layer 1 data
            assert response.company_name == "Example"


class TestSocialMediaNormalization:
    """Test social media handle and URL normalization"""

    @pytest.mark.parametrize("input_handle,expected_url", SOCIAL_MEDIA_TESTS["instagram"]["handles"])
    def test_instagram_normalization(self, input_handle, expected_url):
        """Test Instagram handle normalization"""
        from app.utils.social_media import normalize_instagram

        result = normalize_instagram(input_handle)
        assert result == expected_url

    @pytest.mark.parametrize("input_handle,expected_url", SOCIAL_MEDIA_TESTS["tiktok"]["handles"])
    def test_tiktok_normalization(self, input_handle, expected_url):
        """Test TikTok handle normalization"""
        from app.utils.social_media import normalize_tiktok

        result = normalize_tiktok(input_handle)
        assert result == expected_url


class TestPhoneFormatting:
    """Test phone number formatting and validation"""

    @pytest.mark.parametrize("input_phone,expected_format", PHONE_TESTS["brazilian"])
    def test_brazilian_phone_formatting(self, input_phone, expected_format):
        """Test Brazilian phone number formatting"""
        from app.utils.phone_formatter import format_brazilian_phone

        result = format_brazilian_phone(input_phone)
        assert result == expected_format

    def test_whatsapp_number_extraction(self):
        """Test WhatsApp number extraction from wa.me links"""
        from app.utils.phone_formatter import extract_whatsapp_number

        url = "https://wa.me/5511987654321"
        result = extract_whatsapp_number(url)

        assert result == "+55 11 98765-4321"


class TestURLValidation:
    """Test URL validation and auto-prefixing"""

    @pytest.mark.parametrize("input_url,expected_url", URL_TESTS["auto_prefix"])
    def test_url_auto_prefix(self, input_url, expected_url):
        """Test that URLs are auto-prefixed with https://"""
        from app.utils.url_validator import normalize_url

        result = normalize_url(input_url)
        assert result == expected_url

    @pytest.mark.parametrize("valid_url", URL_TESTS["validation"]["valid"])
    def test_valid_urls(self, valid_url):
        """Test URL validation accepts valid URLs"""
        from app.utils.url_validator import is_valid_url

        assert is_valid_url(valid_url) is True

    @pytest.mark.parametrize("invalid_url", URL_TESTS["validation"]["invalid"])
    def test_invalid_urls(self, invalid_url):
        """Test URL validation rejects invalid URLs"""
        from app.utils.url_validator import is_valid_url

        assert is_valid_url(invalid_url) is False
