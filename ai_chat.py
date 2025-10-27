"""
AI Chat System for Strategic Analysis Reports

Allows admins to ask questions about generated reports to verify accuracy,
understand AI reasoning, and get clarifications.

System Prompt Context:
- Full access to company submission data
- Full access to generated report JSON
- Full access to data quality metrics
- Can explain reasoning behind recommendations
- Can validate assumptions
- Can suggest improvements
"""

import anthropic
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json


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
    model: str = "claude-3-5-haiku-20241022"
) -> Dict[str, Any]:
    """
    Send a chat message and get AI response

    Args:
        submission_data: Company submission data
        report_data: Generated report JSON
        data_quality: Data quality metrics
        chat_history: Previous messages [{"role": "user"|"assistant", "content": "..."}]
        user_message: New message from user
        model: Claude model to use (haiku for speed/cost, sonnet for quality)

    Returns:
        {
            "message": str,           # AI response
            "model_used": str,        # Model that was used
            "tokens_used": int,       # Approximate tokens
            "timestamp": str,         # ISO timestamp
        }
    """

    try:
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Create system prompt with full context
        system_prompt = create_chat_system_prompt(submission_data, report_data, data_quality)

        # Build messages array (history + new message)
        messages = chat_history + [{"role": "user", "content": user_message}]

        # Call Claude API
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            temperature=0.7,
            system=system_prompt,
            messages=messages
        )

        # Extract response
        assistant_message = response.content[0].text

        # Calculate approximate tokens (Claude API doesn't return token count directly)
        # Rough estimate: 1 token ≈ 4 characters
        tokens_used = len(system_prompt + user_message + assistant_message) // 4

        return {
            "message": assistant_message,
            "model_used": model,
            "tokens_used": tokens_used,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": True
        }

    except anthropic.APIError as e:
        print(f"[AI CHAT ERROR] Anthropic API error: {e}")
        return {
            "message": f"Error calling AI: {str(e)}",
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
            user_message="Por que você recomendou focar em B2B?"
        )

        print(f"AI Response: {result['message']}")
        print(f"Model: {result['model_used']}")
        print(f"Tokens: {result['tokens_used']}")

    asyncio.run(test_chat())
