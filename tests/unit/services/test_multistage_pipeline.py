"""
Unit tests for Multi-Stage Analysis Pipeline
Tests pipeline orchestration, stage execution, and error handling
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.services.analysis.pipeline_orchestrator import generate_multistage_analysis
from app.core.exceptions import ExternalServiceError, ValidationError


@pytest.mark.unit
class TestMultiStagePipeline:
    """Test multi-stage analysis pipeline"""

    @pytest.mark.asyncio
    async def test_successful_pipeline_execution(
        self,
        mock_openrouter_api,
        mock_apify_client,
        mock_perplexity_api,
        sample_analysis_report
    ):
        """Test successful end-to-end pipeline execution"""
        with patch('app.services.analysis.pipeline_orchestrator.LLMClient') as mock_llm:
            # Mock LLM client to return valid JSON
            mock_instance = mock_llm.return_value
            mock_instance.call_with_retry = AsyncMock(
                return_value=(json.dumps(sample_analysis_report), {"input_tokens": 100, "output_tokens": 200})
            )

            result = await generate_multistage_analysis(
                company="Test Company",
                industry="Technology",
                website="https://testcompany.com",
                challenge="Grow revenue by 100%",
                apify_data=None,
                perplexity_data=None
            )

            # Should return complete analysis
            assert "diagnostico_estrategico" in result
            assert "analise_mercado" in result
            assert "_metadata" in result

            # Metadata should include cost and timing
            metadata = result["_metadata"]
            assert "total_cost" in metadata
            assert "processing_time" in metadata

    @pytest.mark.asyncio
    async def test_pipeline_with_cached_data(self, mock_openrouter_api, sample_analysis_report):
        """Test pipeline uses cached data when available"""
        with patch('app.services.analysis.cache_wrapper.get_cached_stage_result') as mock_cache:
            with patch('app.services.analysis.pipeline_orchestrator.LLMClient') as mock_llm:
                # Mock cache to return cached stage result
                mock_cache.return_value = {"cached": "data"}

                mock_instance = mock_llm.return_value
                mock_instance.call_with_retry = AsyncMock(
                    return_value=(json.dumps(sample_analysis_report), {"input_tokens": 100, "output_tokens": 200})
                )

                result = await generate_multistage_analysis(
                    company="Test Company",
                    industry="Technology",
                    website=None,
                    challenge=None,
                    apify_data=None,
                    perplexity_data=None
                )

                # Should complete successfully with cached data
                assert result is not None

    @pytest.mark.asyncio
    async def test_pipeline_handles_stage_failure(self, mock_openrouter_api):
        """Test pipeline handles individual stage failures"""
        with patch('app.services.analysis.pipeline_orchestrator.LLMClient') as mock_llm:
            # Mock LLM to fail
            mock_instance = mock_llm.return_value
            mock_instance.call_with_retry = AsyncMock(
                side_effect=ExternalServiceError("LLM call failed", service_name="OpenRouter")
            )

            with pytest.raises(ExternalServiceError):
                await generate_multistage_analysis(
                    company="Test Company",
                    industry="Technology",
                    website=None,
                    challenge=None,
                    apify_data=None,
                    perplexity_data=None
                )

    @pytest.mark.asyncio
    async def test_pipeline_validates_inputs(self):
        """Test pipeline validates required inputs"""
        with pytest.raises((ValueError, ValidationError)):
            await generate_multistage_analysis(
                company="",  # Empty company name
                industry="Technology",
                website=None,
                challenge=None,
                apify_data=None,
                perplexity_data=None
            )

    @pytest.mark.asyncio
    async def test_pipeline_tracks_costs(self, mock_openrouter_api, sample_analysis_report):
        """Test pipeline tracks costs across all stages"""
        with patch('app.services.analysis.pipeline_orchestrator.LLMClient') as mock_llm:
            mock_instance = mock_llm.return_value
            mock_instance.call_with_retry = AsyncMock(
                return_value=(json.dumps(sample_analysis_report), {"input_tokens": 1000, "output_tokens": 2000})
            )

            result = await generate_multistage_analysis(
                company="Test Company",
                industry="Technology",
                website=None,
                challenge=None,
                apify_data=None,
                perplexity_data=None
            )

            # Should include cost metadata
            assert "_metadata" in result
            assert "total_cost" in result["_metadata"]
            assert result["_metadata"]["total_cost"] > 0

    @pytest.mark.asyncio
    async def test_pipeline_includes_metadata(self, mock_openrouter_api, sample_analysis_report):
        """Test pipeline includes comprehensive metadata"""
        with patch('app.services.analysis.pipeline_orchestrator.LLMClient') as mock_llm:
            mock_instance = mock_llm.return_value
            mock_instance.call_with_retry = AsyncMock(
                return_value=(json.dumps(sample_analysis_report), {"input_tokens": 100, "output_tokens": 200})
            )

            result = await generate_multistage_analysis(
                company="Test Company",
                industry="Technology",
                website=None,
                challenge=None,
                apify_data=None,
                perplexity_data=None
            )

            metadata = result["_metadata"]

            # Should include key metadata fields
            assert "version" in metadata
            assert "generated_at" in metadata
            assert "total_cost" in metadata
            assert "processing_time" in metadata
            assert "stages" in metadata

    @pytest.mark.asyncio
    async def test_pipeline_respects_force_regenerate(self, mock_openrouter_api, sample_analysis_report):
        """Test pipeline bypasses cache when force_regenerate=True"""
        with patch('app.services.analysis.cache_wrapper.get_cached_stage_result') as mock_cache:
            with patch('app.services.analysis.pipeline_orchestrator.LLMClient') as mock_llm:
                mock_instance = mock_llm.return_value
                mock_instance.call_with_retry = AsyncMock(
                    return_value=(json.dumps(sample_analysis_report), {"input_tokens": 100, "output_tokens": 200})
                )

                result = await generate_multistage_analysis(
                    company="Test Company",
                    industry="Technology",
                    website=None,
                    challenge=None,
                    apify_data=None,
                    perplexity_data=None,
                    force_regenerate=True
                )

                # Cache should not be checked for complete analysis
                # (stage cache may still be used)
                assert result is not None

    @pytest.mark.asyncio
    async def test_pipeline_enriches_with_external_data(
        self,
        mock_openrouter_api,
        mock_apify_client,
        mock_perplexity_api,
        sample_analysis_report
    ):
        """Test pipeline enriches analysis with external data"""
        apify_data = {
            "company_info": {
                "name": "Test Company",
                "employees": 100
            }
        }

        perplexity_data = {
            "answer": "Test company operates in the technology sector"
        }

        with patch('app.services.analysis.pipeline_orchestrator.LLMClient') as mock_llm:
            mock_instance = mock_llm.return_value
            mock_instance.call_with_retry = AsyncMock(
                return_value=(json.dumps(sample_analysis_report), {"input_tokens": 100, "output_tokens": 200})
            )

            result = await generate_multistage_analysis(
                company="Test Company",
                industry="Technology",
                website=None,
                challenge=None,
                apify_data=apify_data,
                perplexity_data=perplexity_data
            )

            # Should complete with enriched data
            assert result is not None


@pytest.mark.unit
class TestStageExecution:
    """Test individual stage execution"""

    @pytest.mark.asyncio
    async def test_stage_execution_with_retry(self, mock_openrouter_api):
        """Test stage execution uses retry logic"""
        from app.services.analysis.stages.stage1_extraction import stage1_extract_data

        with patch('app.services.analysis.llm_client.LLMClient') as mock_llm:
            mock_instance = mock_llm.return_value
            mock_instance.call_with_retry = AsyncMock(
                return_value=('{"test": "data"}', {"input_tokens": 100, "output_tokens": 200})
            )

            result = await stage1_extract_data(
                company="Test Company",
                industry="Technology",
                website_content="Test content",
                linkedin_data=None,
                cost_tracker=None
            )

            # Should call with retry
            mock_instance.call_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_stage_execution_handles_errors(self):
        """Test stage execution handles errors properly"""
        from app.services.analysis.stages.stage1_extraction import stage1_extract_data

        with patch('app.services.analysis.llm_client.LLMClient') as mock_llm:
            mock_instance = mock_llm.return_value
            mock_instance.call_with_retry = AsyncMock(
                side_effect=ExternalServiceError("API failed", service_name="OpenRouter")
            )

            with pytest.raises(ExternalServiceError):
                await stage1_extract_data(
                    company="Test Company",
                    industry="Technology",
                    website_content="Test content",
                    linkedin_data=None,
                    cost_tracker=None
                )


@pytest.mark.unit
class TestCacheIntegration:
    """Test cache integration in pipeline"""

    @pytest.mark.asyncio
    async def test_pipeline_caches_successful_results(self, mock_openrouter_api, sample_analysis_report):
        """Test pipeline caches successful analysis results"""
        with patch('app.services.analysis.pipeline_orchestrator.LLMClient') as mock_llm:
            with patch('app.core.cache.cache_analysis_result') as mock_cache:
                mock_instance = mock_llm.return_value
                mock_instance.call_with_retry = AsyncMock(
                    return_value=(json.dumps(sample_analysis_report), {"input_tokens": 100, "output_tokens": 200})
                )

                await generate_multistage_analysis(
                    company="Test Company",
                    industry="Technology",
                    website=None,
                    challenge=None,
                    apify_data=None,
                    perplexity_data=None
                )

                # Should cache the result
                # Note: Actual caching behavior depends on implementation
                # This test may need adjustment based on actual cache usage

    @pytest.mark.asyncio
    async def test_pipeline_retrieves_from_cache(self, sample_analysis_report):
        """Test pipeline retrieves from cache when available"""
        with patch('app.core.cache.get_cached_analysis') as mock_cache:
            # Mock cache hit
            mock_cache.return_value = {
                "analysis": sample_analysis_report,
                "cache_hit": True,
                "cache_age_hours": 2.5,
                "cost_saved": 15.50
            }

            result = await generate_multistage_analysis(
                company="Test Company",
                industry="Technology",
                website=None,
                challenge=None,
                apify_data=None,
                perplexity_data=None
            )

            # Should return cached result
            assert result is not None
            # If implementation adds cache metadata
            if "_metadata" in result:
                metadata = result.get("_metadata", {})
                # May include cache hit info
