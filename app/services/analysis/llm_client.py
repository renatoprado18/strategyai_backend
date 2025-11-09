"""
LLM Client Module - Handles all LLM API calls with retry logic
Extracted from multistage.py for better code organization
"""

import json
import httpx
import logging
import os
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

from app.utils.validation import CostTracker
from app.core.exceptions import ExternalServiceError, ValidationError
from app.core.constants import (
    LLM_TIMEOUT_DEFAULT,
    LLM_MAX_RETRIES,
    LLM_RETRY_TEMPERATURE_DECAY
)

logger = logging.getLogger(__name__)
load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT = LLM_TIMEOUT_DEFAULT
MAX_RETRIES = LLM_MAX_RETRIES

# Content policy refusal patterns
REFUSAL_PATTERNS = [
    "i'm sorry, i can't assist",
    "i cannot assist",
    "i can't help with that",
    "i cannot help with that",
    "desculpe, não posso ajudar",
    "não posso ajudar com isso"
]


class LLMClient:
    """
    Centralized LLM client for OpenRouter API calls
    Handles retries, error handling, and response parsing
    """

    def __init__(self, api_key: str = None, timeout: float = TIMEOUT):
        self.api_key = api_key or OPENROUTER_API_KEY
        if not self.api_key:
            raise ValidationError("OPENROUTER_API_KEY not set")
        self.timeout = timeout

    async def call_with_retry(
        self,
        stage_name: str,
        model: str,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        max_retries: int = MAX_RETRIES,
        cost_tracker: Optional[CostTracker] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Call LLM with automatic retry logic and progressive temperature reduction

        Args:
            stage_name: Name of the stage for logging
            model: Model to use
            prompt: User prompt
            system_prompt: System prompt
            temperature: Initial temperature (will be reduced on retries)
            max_tokens: Max tokens
            max_retries: Maximum retry attempts
            cost_tracker: Optional CostTracker instance

        Returns:
            (valid_json_string, usage_stats)

        Raises:
            ValidationError: If content policy refusal is detected
            ExternalServiceError: If LLM call fails after all retries
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # Reduce temperature on retries for more deterministic output
                current_temp = temperature * (LLM_RETRY_TEMPERATURE_DECAY ** attempt)

                # Make prompt stricter on retries
                if attempt > 0:
                    strict_prompt = (
                        f"{prompt}\n\n"
                        "**CRITICAL: Output ONLY valid JSON. "
                        "No markdown, no code blocks, no explanations. "
                        "Start with {{ and end with }}.**"
                    )
                    logger.warning(
                        f"[{stage_name}] Retry {attempt + 1}/{max_retries} "
                        f"with temperature {current_temp:.2f}"
                    )
                else:
                    strict_prompt = prompt

                response, usage_stats = await self.call(
                    model=model,
                    prompt=strict_prompt,
                    system_prompt=system_prompt or "Output JSON ONLY. No markdown. No explanations.",
                    temperature=current_temp,
                    max_tokens=max_tokens
                )

                # Check for content policy refusals BEFORE validating JSON
                if self._is_refusal(response):
                    logger.warning(f"[{stage_name}] Content policy refusal detected: {response[:100]}")
                    raise ValidationError(f"Content policy refusal: {response[:100]}")

                # Validate JSON
                json.loads(response)  # Will raise JSONDecodeError if invalid

                # Log usage to cost tracker
                if cost_tracker:
                    cost_tracker.log_usage(
                        stage_name,
                        model,
                        usage_stats["input_tokens"],
                        usage_stats["output_tokens"]
                    )

                logger.info(f"[{stage_name}] ✅ Valid JSON received (attempt {attempt + 1})")
                return response, usage_stats

            except json.JSONDecodeError as e:
                last_error = e
                logger.error(f"[{stage_name}] JSON parse error on attempt {attempt + 1}: {e}")
                if 'response' in locals():
                    logger.error(f"[{stage_name}] Response preview: {response[:1000]}")

                if attempt == max_retries - 1:
                    logger.error(f"[{stage_name}] All {max_retries} attempts failed!")
                    if 'response' in locals():
                        logger.error(f"[{stage_name}] Full response: {response}")
                    raise ExternalServiceError(
                        f"{stage_name} failed after {max_retries} attempts: {e}",
                        service_name="OpenRouter"
                    )

            except ValidationError as e:
                # Content policy refusal - preserve ValidationError type for fallback handling
                last_error = e
                logger.error(f"[{stage_name}] LLM call failed on attempt {attempt + 1}: {str(e)}")

                if attempt == max_retries - 1:
                    raise ValidationError(f"{stage_name} failed after {max_retries} attempts: {str(e)}")

            except Exception as e:
                last_error = e
                logger.error(f"[{stage_name}] LLM call failed on attempt {attempt + 1}: {str(e)}")

                if attempt == max_retries - 1:
                    raise ExternalServiceError(
                        f"{stage_name} failed after {max_retries} attempts: {str(e)}",
                        service_name="OpenRouter"
                    )

        # Should never reach here, but just in case
        raise ExternalServiceError(
            f"{stage_name} failed: {last_error}",
            service_name="OpenRouter"
        )

    async def call(
        self,
        model: str,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: str = "json"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generic LLM caller for any OpenRouter model

        Args:
            model: Model identifier (e.g., "google/gemini-flash-1.5")
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            response_format: Expected response format ("json" or "text")

        Returns:
            (content, usage_stats) where usage_stats = {"input_tokens": int, "output_tokens": int}

        Raises:
            ExternalServiceError: If API call fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://strategy-ai.com",
            "X-Title": "Strategy AI - Multi-Stage Analysis",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"[LLM] Calling {model} (prompt: {len(prompt)} chars)")

                response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
                response.raise_for_status()

                data = response.json()

                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"].strip()

                    # Clean markdown code blocks if JSON expected
                    if response_format == "json":
                        content = self._clean_json_response(content)

                    # Extract usage stats
                    usage = data.get("usage", {})
                    usage_stats = {
                        "input_tokens": usage.get("prompt_tokens", 0),
                        "output_tokens": usage.get("completion_tokens", 0)
                    }

                    logger.info(
                        f"[LLM] {model} responded ({len(content)} chars, "
                        f"{usage_stats['input_tokens']} in, {usage_stats['output_tokens']} out)"
                    )
                    return content, usage_stats
                else:
                    raise ExternalServiceError(
                        f"Unexpected API response: {data}",
                        service_name="OpenRouter"
                    )

        except httpx.TimeoutException as e:
            logger.error(f"[LLM] Timeout calling {model}: {e}")
            raise ExternalServiceError(
                f"LLM call to {model} timed out after {self.timeout}s",
                service_name="OpenRouter"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"[LLM] HTTP error calling {model}: {e.response.status_code} - {e.response.text}")
            raise ExternalServiceError(
                f"OpenRouter API error: {e.response.status_code} - {e.response.text}",
                service_name="OpenRouter"
            )
        except ExternalServiceError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"[LLM] Unexpected error calling {model}: {e}")
            raise ExternalServiceError(
                f"LLM call failed: {str(e)}",
                service_name="OpenRouter"
            )

    def _clean_json_response(self, content: str) -> str:
        """Clean markdown code blocks from JSON responses"""
        # Handle markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()

        # Try to find JSON object if embedded in text
        if not content.startswith("{") and "{" in content:
            json_start = content.find("{")
            content = content[json_start:]

        # Find matching closing brace
        if content.startswith("{"):
            brace_count = 0
            for i, char in enumerate(content):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        content = content[:i+1]
                        break

        return content

    def _is_refusal(self, response: str) -> bool:
        """Check if response contains content policy refusal"""
        response_lower = response.lower()
        return any(pattern in response_lower for pattern in REFUSAL_PATTERNS)


# Legacy function wrappers for backward compatibility
async def call_llm_with_retry(*args, **kwargs) -> Tuple[str, Dict[str, Any]]:
    """
    Legacy wrapper for backward compatibility
    Deprecated: Use LLMClient().call_with_retry() instead
    """
    client = LLMClient()
    return await client.call_with_retry(*args, **kwargs)


async def call_llm(*args, **kwargs) -> Tuple[str, Dict[str, Any]]:
    """
    Legacy wrapper for backward compatibility
    Deprecated: Use LLMClient().call() instead
    """
    client = LLMClient()
    return await client.call(*args, **kwargs)
