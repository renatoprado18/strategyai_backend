"""
AI Chat System for Strategic Analysis Reports

Allows admins to ask questions about generated reports to verify accuracy,
understand AI reasoning, and get clarifications.

Uses OpenRouter API (same as main analysis) for consistency and cost optimization.

System Prompt Context:
- Full access to company submission data
- Full access to generated report JSON
- Full access to data quality metrics
- Can explain reasoning behind recommendations
- Can validate assumptions
- Can suggest improvements
"""

import httpx
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model mapping for chat (OpenRouter model IDs)
CHAT_MODELS = {
    "haiku": "anthropic/claude-3.5-haiku-20241022",  # Fast & cheap
    "sonnet": "anthropic/claude-3.5-sonnet-20241022",  # High quality
}

TIMEOUT = 60.0


def create_chat_system_prompt(
    submission_data: Dict[str, Any],
    report_data: Dict[str, Any],
    data_quality: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create system prompt with full context about the analysis

    Args:
        submission_data: Original submission (company, industry, challenge, etc.)
        report_data: Generated analysis report JSON
        data_quality: Data quality metrics

    Returns:
        System prompt string with full context
    """

    # Build context
    context = f"""You are the AI analyst that generated this strategic analysis report.

## Company Information
Company: {submission_data.get('company')}
Industry: {submission_data.get('industry')}
Challenge: {submission_data.get('challenge', 'Not specified')}
Website: {submission_data.get('website', 'Not provided')}

## Analysis Generated
You completed a comprehensive strategic analysis using 12-13 frameworks including:
- PESTEL Analysis
- Porter's 7 Forces
- SWOT Analysis
- Blue Ocean Strategy
- TAM/SAM/SOM Market Sizing
- Balanced Scorecard
- OKRs
- Growth Hacking Loops
- Scenario Planning
- Priority Recommendations
- Multi-Criteria Decision Matrix

"""

    # Add data quality context if available
    if data_quality:
        tier = data_quality.get('quality_tier', 'unknown')
        sources_succeeded = data_quality.get('sources_succeeded', 0)
        sources_failed = data_quality.get('sources_failed', 0)

        context += f"""## Data Quality
Quality Tier: {tier.upper()}
Sources Succeeded: {sources_succeeded}
Sources Failed: {sources_failed}
Data Completeness: {data_quality.get('data_completeness', 'Unknown')}

"""

    # Add key insights from report
    context += """## Your Role
- Answer questions about the analysis you generated
- Explain your reasoning behind recommendations
- Clarify assumptions made
- Suggest improvements if asked
- Be honest about data limitations
- Reference specific sections of the report when relevant

## Response Guidelines
- Be concise but thorough
- Cite specific data points when possible
- Acknowledge limitations or uncertainties
- Suggest follow-up research if data was insufficient
- Use professional consulting language
- Format responses clearly with bullet points when appropriate

User is an admin reviewing the report before sending to client. Help them verify accuracy and understand your analysis."""

    return context


async def send_chat_message(
    submission_data: Dict[str, Any],
    report_data: Dict[str, Any],
    data_quality: Optional[Dict[str, Any]],
    chat_history: List[Dict[str, str]],
    user_message: str,
    model: str = "haiku"
) -> Dict[str, Any]:
    """
    Send a chat message and get AI response

    Args:
        submission_data: Company submission data
        report_data: Generated report JSON
        data_quality: Data quality metrics
        chat_history: Previous messages [{"role": "user"|"assistant", "content": "..."}]
        user_message: New message from user
        model: "haiku" (fast/cheap) or "sonnet" (high quality)

    Returns:
        {
            "message": str,           # AI response
            "model_used": str,        # Model that was used
            "tokens_used": int,       # Approximate tokens
            "timestamp": str,         # ISO timestamp
        }
    """

    try:
        # Get OpenRouter model ID
        openrouter_model = CHAT_MODELS.get(model, CHAT_MODELS["haiku"])

        # Create system prompt with full context
        system_prompt = create_chat_system_prompt(submission_data, report_data, data_quality)

        # Build messages array (system + history + new message)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(chat_history)
        messages.append({"role": "user", "content": user_message})

        # Prepare request
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://strategy-ai.com",
            "X-Title": "Strategy AI - Chat System",
        }

        payload = {
            "model": openrouter_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        # Call OpenRouter API
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                assistant_message = data["choices"][0]["message"]["content"].strip()

                # Calculate approximate tokens
                tokens_used = data.get("usage", {}).get("total_tokens", 0)

                return {
                    "message": assistant_message,
                    "model_used": openrouter_model,
                    "tokens_used": tokens_used,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "success": True
                }
            else:
                raise Exception("No response from OpenRouter")

    except httpx.HTTPStatusError as e:
        print(f"[AI CHAT ERROR] OpenRouter HTTP error: {e.response.status_code} - {e.response.text}")
        return {
            "message": f"Error calling AI: HTTP {e.response.status_code}",
            "model_used": model,
            "tokens_used": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        print(f"[AI CHAT ERROR] Unexpected error: {e}")
        return {
            "message": f"Unexpected error: {str(e)}",
            "model_used": model,
            "tokens_used": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": False,
            "error": str(e)
        }


def get_quick_prompts() -> List[Dict[str, str]]:
    """
    Get list of quick prompt suggestions for common questions

    Returns:
        List of {label, prompt} dictionaries
    """
    return [
        {
            "label": "Explicar Recomendação Principal",
            "prompt": "Por que você recomendou [primeira recomendação]? Quais dados suportam isso?"
        },
        {
            "label": "Riscos Principais",
            "prompt": "Quais são os 3 maiores riscos que identifiquei para esta empresa?"
        },
        {
            "label": "Confiança na Análise",
            "prompt": "Quão confiante você está nesta análise? Onde os dados eram mais fracos?"
        },
        {
            "label": "Validar TAM/SAM/SOM",
            "prompt": "Como você chegou aos números de TAM/SAM/SOM? Eles são realistas?"
        },
        {
            "label": "Próximos Passos",
            "prompt": "Se você fosse o CEO, qual seria seu primeiro passo amanhã?"
        },
        {
            "label": "Dados Faltantes",
            "prompt": "Que dados adicionais melhorariam significativamente esta análise?"
        }
    ]


# Example usage
if __name__ == "__main__":
    import asyncio

    # Test data
    test_submission = {
        "id": 1,
        "company": "TechCorp Brasil",
        "industry": "Tecnologia",
        "challenge": "Expandir mercado B2B",
        "website": "https://techcorp.com.br"
    }

    test_report = {
        "sumario_executivo": "TechCorp tem potencial de crescimento no mercado B2B...",
        "analise_swot": {
            "forças": ["Tecnologia inovadora", "Equipe experiente"],
            "fraquezas": ["Marca pouco conhecida"],
            "oportunidades": ["Mercado B2B em crescimento"],
            "ameaças": ["Concorrência internacional"]
        }
    }

    test_quality = {
        "quality_tier": "good",
        "sources_succeeded": 5,
        "sources_failed": 1,
        "data_completeness": "75%"
    }

    async def test_chat():
        # Test message
        result = await send_chat_message(
            submission_data=test_submission,
            report_data=test_report,
            data_quality=test_quality,
            chat_history=[],
            user_message="Por que você recomendou focar em B2B?",
            model="haiku"
        )

        print(f"AI Response: {result['message']}")
        print(f"Model: {result['model_used']}")
        print(f"Tokens: {result['tokens_used']}")

    asyncio.run(test_chat())
