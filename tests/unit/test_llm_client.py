"""
Unit tests for LLM Client
Tests the LLM client with retry logic, error handling, and response parsing
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
import httpx

from app.services.analysis.llm_client import LLMClient
from app.core.exceptions import ExternalServiceError, ValidationError


@pytest.mark.unit
class TestLLMClient:
    """Test suite for LLM Client"""

    @pytest.fixture
    def llm_client(self):
        """Create LLM client instance for testing"""
        return LLMClient(api_key="test-key-123", timeout=10.0)

    @pytest.mark.asyncio
    async def test_successful_call(self, llm_client):
        """Test successful LLM API call"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"test": "data"}'
                }
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50
            }
        }

        with patch('httpx.AsyncClient.post', return_value=mock_response):
            content, usage = await llm_client.call(
                model="test-model",
                prompt="test prompt",
                system_prompt="test system"
            )

            assert content == '{"test": "data"}'
            assert usage["input_tokens"] == 100
            assert usage["output_tokens"] == 50

    @pytest.mark.asyncio
    async def test_call_with_retry_success_on_first_attempt(self, llm_client):
        """Test call_with_retry succeeds on first attempt"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"result": "success"}'
                }
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50
            }
        }

        with patch('httpx.AsyncClient.post', return_value=mock_response):
            content, usage = await llm_client.call_with_retry(
                stage_name="test_stage",
                model="test-model",
                prompt="test prompt",
                max_retries=3
            )

            assert json.loads(content) == {"result": "success"}
            assert usage["input_tokens"] == 100

    @pytest.mark.asyncio
    async def test_call_with_retry_recovers_from_invalid_json(self, llm_client):
        """Test call_with_retry recovers from invalid JSON on retry"""
        # First call returns invalid JSON, second call succeeds
        call_count = [0]

        def mock_post(*args, **kwargs):
            call_count[0] += 1
            mock_response = Mock()
            mock_response.status_code = 200

            if call_count[0] == 1:
                # First call: invalid JSON
                mock_response.json.return_value = {
                    "choices": [{
                        "message": {
                            "content": "This is not valid JSON"
                        }
                    }],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50}
                }
            else:
                # Second call: valid JSON
                mock_response.json.return_value = {
                    "choices": [{
                        "message": {
                            "content": '{"result": "success"}'
                        }
                    }],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50}
                }

            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            content, usage = await llm_client.call_with_retry(
                stage_name="test_stage",
                model="test-model",
                prompt="test prompt",
                max_retries=3
            )

            assert json.loads(content) == {"result": "success"}
            assert call_count[0] == 2  # Should have retried once

    @pytest.mark.asyncio
    async def test_call_with_retry_fails_after_max_retries(self, llm_client):
        """Test call_with_retry fails after exhausting retries"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Invalid JSON every time"
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }

        with patch('httpx.AsyncClient.post', return_value=mock_response):
            with pytest.raises(ExternalServiceError) as exc_info:
                await llm_client.call_with_retry(
                    stage_name="test_stage",
                    model="test-model",
                    prompt="test prompt",
                    max_retries=2
                )

            assert "test_stage failed after 2 attempts" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_content_policy_refusal_detection(self, llm_client):
        """Test detection of content policy refusals"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "I'm sorry, I can't assist with that request."
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }

        with patch('httpx.AsyncClient.post', return_value=mock_response):
            with pytest.raises(ValidationError) as exc_info:
                await llm_client.call_with_retry(
                    stage_name="test_stage",
                    model="test-model",
                    prompt="test prompt",
                    max_retries=1
                )

            assert "Content policy refusal" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_timeout_error(self, llm_client):
        """Test handling of HTTP timeout errors"""
        with patch('httpx.AsyncClient.post', side_effect=httpx.TimeoutException("Timeout")):
            with pytest.raises(ExternalServiceError) as exc_info:
                await llm_client.call(
                    model="test-model",
                    prompt="test prompt"
                )

            assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_status_error(self, llm_client):
        """Test handling of HTTP status errors"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = mock_response
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=Mock(),
                response=mock_response
            )

            with pytest.raises(ExternalServiceError) as exc_info:
                await llm_client.call(
                    model="test-model",
                    prompt="test prompt"
                )

            assert "OpenRouter API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_clean_json_response_with_markdown(self, llm_client):
        """Test cleaning JSON response wrapped in markdown code blocks"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '```json\n{"result": "success"}\n```'
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }

        with patch('httpx.AsyncClient.post', return_value=mock_response):
            content, usage = await llm_client.call(
                model="test-model",
                prompt="test prompt",
                response_format="json"
            )

            assert content == '{"result": "success"}'

    @pytest.mark.asyncio
    async def test_temperature_decay_on_retries(self, llm_client):
        """Test that temperature decreases on retries"""
        call_count = [0]
        temperatures = []

        def mock_post(*args, **kwargs):
            call_count[0] += 1
            # Capture the temperature from the request
            payload = kwargs.get('json', {})
            temperatures.append(payload.get('temperature', 0.7))

            mock_response = Mock()
            mock_response.status_code = 200

            if call_count[0] < 3:
                # Return invalid JSON to force retry
                mock_response.json.return_value = {
                    "choices": [{
                        "message": {"content": "Invalid"}
                    }],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50}
                }
            else:
                # Return valid JSON on third attempt
                mock_response.json.return_value = {
                    "choices": [{
                        "message": {"content": '{"success": true}'}
                    }],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50}
                }

            return mock_response

        with patch('httpx.AsyncClient.post', side_effect=mock_post):
            await llm_client.call_with_retry(
                stage_name="test_stage",
                model="test-model",
                prompt="test prompt",
                temperature=0.7,
                max_retries=3
            )

            # Verify temperature decreased on retries
            assert len(temperatures) == 3
            assert temperatures[0] > temperatures[1] > temperatures[2]

    @pytest.mark.asyncio
    async def test_cost_tracker_integration(self, llm_client, mock_cost_tracker):
        """Test integration with cost tracker"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": '{"result": "success"}'}
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 200
            }
        }

        with patch('httpx.AsyncClient.post', return_value=mock_response):
            await llm_client.call_with_retry(
                stage_name="test_stage",
                model="test-model",
                prompt="test prompt",
                cost_tracker=mock_cost_tracker
            )

            # Verify cost was logged
            assert mock_cost_tracker.total_cost > 0

    def test_is_refusal_detection(self, llm_client):
        """Test refusal pattern detection"""
        assert llm_client._is_refusal("I'm sorry, I can't assist with that")
        assert llm_client._is_refusal("I cannot help with that request")
        assert llm_client._is_refusal("Desculpe, não posso ajudar")
        assert not llm_client._is_refusal("Here is your analysis")

    def test_clean_json_response_with_text_prefix(self, llm_client):
        """Test cleaning JSON with text prefix"""
        content = "Here is the JSON: {'result': 'success'}"
        cleaned = llm_client._clean_json_response(content)
        assert cleaned.startswith("{")

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """Test that missing API key raises error"""
        with pytest.raises(ValidationError) as exc_info:
            LLMClient(api_key=None)

        assert "OPENROUTER_API_KEY not set" in str(exc_info.value)
