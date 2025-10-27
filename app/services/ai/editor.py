"""
AI-Powered Report Editor
Adaptive model selection: Gemini Flash (cheap) for simple edits, Claude Haiku for complex
"""

import json
import logging
import re
from typing import Dict, Any, Optional, AsyncIterator
import httpx
import os
from dotenv import load_dotenv

# Import prompt injection sanitization
from app.core.security.prompt_sanitizer import sanitize_for_prompt, validate_instruction

logger = logging.getLogger(__name__)
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Models for adaptive selection
MODEL_SIMPLE = "google/gemini-2.5-flash-preview-09-2025"  # $0.075/M in, $0.30/M out
MODEL_COMPLEX = "anthropic/claude-haiku-4.5"  # $0.25/M in, $1.25/M out

TIMEOUT = 60.0


# ============================================================================
# EDIT COMPLEXITY CLASSIFICATION
# ============================================================================

def classify_edit_complexity(instruction: str, selected_text: str) -> str:
    """
    Classify if an edit instruction is simple or complex

    Simple edits: rewording, shortening, tone changes, simple replacements
    Complex edits: adding analysis, restructuring, combining ideas, deep refinement

    Args:
        instruction: User's edit instruction
        selected_text: The text being edited

    Returns:
        "simple" or "complex"
    """

    instruction_lower = instruction.lower()

    # Simple edit indicators
    simple_keywords = [
        "shorter", "longer", "concise", "professional", "casual",
        "fix", "typo", "grammar", "change", "replace",
        "more formal", "less formal", "simpler", "clearer"
    ]

    # Complex edit indicators
    complex_keywords = [
        "rewrite", "expand", "detail", "analyze", "add analysis",
        "combine", "restructure", "focus on", "incorporate",
        "add context", "explain why", "add data", "add examples"
    ]

    # Check for complex keywords first (they take priority)
    for keyword in complex_keywords:
        if keyword in instruction_lower:
            return "complex"

    # Check for simple keywords
    for keyword in simple_keywords:
        if keyword in instruction_lower:
            return "simple"

    # Length-based heuristic
    # Short instructions are usually simple
    if len(instruction.split()) <= 5:
        return "simple"

    # If instruction is long and doesn't match simple patterns, it's complex
    if len(instruction.split()) > 10:
        return "complex"

    # Default to simple (cheaper model)
    return "simple"


# ============================================================================
# AI EDIT GENERATION
# ============================================================================

async def generate_edit_suggestion(
    selected_text: str,
    instruction: str,
    section_context: str,
    full_report_summary: Optional[str] = None,
    complexity: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate edit suggestion using adaptive model selection

    Args:
        selected_text: The text user selected to edit
        instruction: User's natural language instruction
        section_context: Surrounding context from the section
        full_report_summary: Optional summary of full report for context
        complexity: Force "simple" or "complex", or None for auto-detect

    Returns:
        {
            "suggested_edit": str,
            "reasoning": str,
            "model_used": str,
            "complexity": str,
            "cost_estimate": float
        }
    """

    # STEP 1: Validate and sanitize instruction (can raise ValueError)
    try:
        instruction = validate_instruction(instruction)
    except ValueError as e:
        logger.error(f"[AI EDITOR] Instruction validation failed: {e}")
        raise Exception(f"Invalid instruction: {str(e)}")

    # STEP 2: Sanitize user-provided text (could be manipulated)
    selected_text = sanitize_for_prompt(selected_text, max_length=2000, strict_mode=True)
    section_context = sanitize_for_prompt(section_context, max_length=1000, strict_mode=True)

    logger.info(f"[AI EDITOR] Inputs sanitized successfully")

    # Auto-detect complexity if not specified
    if complexity is None:
        complexity = classify_edit_complexity(instruction, selected_text)

    # Select model based on complexity
    model = MODEL_SIMPLE if complexity == "simple" else MODEL_COMPLEX

    logger.info(f"[AI EDITOR] Complexity: {complexity}, Model: {model}")

    # Detect if editing an array item (bullet point)
    is_list_item = '[' in section_context

    # Build formatting instructions based on data type
    if is_list_item:
        formatting_instruction = """
**FORMATTING RULES (SINGLE LIST ITEM):**
- You are editing ONE item in a list
- Return EXACTLY ONE sentence/phrase - NOT multiple items
- Return PLAIN TEXT ONLY (no bullets, no dashes, no formatting)
- The text will be displayed as a bullet point automatically
- DO NOT add: •, -, *, or any list markers
- DO NOT add line breaks
- DO NOT split into multiple items
- WRONG: "Item 1 • Item 2 • Item 3"
- CORRECT: "Single edited item text"
"""
    else:
        formatting_instruction = """
**FORMATTING RULES (PARAGRAPH):**
- Preserve paragraph structure
- Maintain line breaks if present
- Keep any bold/emphasis from original
"""

    # Build prompt
    prompt = f"""You are an expert editor helping improve a strategic business report in Portuguese (Brazilian).

**SELECTED TEXT TO EDIT:**
"{selected_text}"

**SECTION CONTEXT:**
{section_context}

**USER INSTRUCTION:**
{instruction}

**YOUR TASK:**
1. Apply the user's instruction to the selected text
2. Keep the edit concise and focused on the selected text only
3. Maintain Brazilian Portuguese
4. Preserve any source citations (fonte:, baseado em, etc.)
5. Keep the same tone and professionalism as the original

{formatting_instruction}

**OUTPUT FORMAT (JSON ONLY):**
{{
  "suggested_edit": "Your edited version of the selected text",
  "reasoning": "Brief explanation of what you changed and why (1-2 sentences)"
}}

**CRITICAL:**
- Output ONLY valid JSON
- Do NOT change text outside the selected portion
- Keep source attributions intact
- Follow the formatting rules exactly
"""

    # Add full report context if available (for complex edits)
    if full_report_summary and complexity == "complex":
        prompt = f"""**FULL REPORT CONTEXT:**
{full_report_summary}

{prompt}"""

    system_prompt = "You are an expert editor. Follow instructions precisely. Output JSON only."

    try:
        # Call LLM
        response_text, usage_stats = await call_llm(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temp for more consistent edits
            max_tokens=2000
        )

        # Parse response
        result = json.loads(response_text)

        # Sanitize formatting for list items (remove stray bullets/markers)
        if is_list_item:
            suggested_edit = result.get("suggested_edit", "").strip()

            # If AI returned multiple items (split by bullets), take ONLY the first one
            for separator in [" • ", " · ", " - ", " | "]:
                if separator in suggested_edit:
                    suggested_edit = suggested_edit.split(separator)[0].strip()
                    logger.warning(f"[AI EDITOR] AI returned multiple items, taking first: {suggested_edit}")
                    break

            # Remove leading bullets/markers
            for marker in ["• ", "- ", "* ", "→ ", "▸ ", "▪ ", "◦ ", "⚠️ "]:
                if suggested_edit.startswith(marker):
                    suggested_edit = suggested_edit[len(marker):].strip()

            result["suggested_edit"] = suggested_edit

        # Calculate cost
        pricing = {
            MODEL_SIMPLE: {"input": 0.075, "output": 0.30},
            MODEL_COMPLEX: {"input": 0.25, "output": 1.25}
        }

        model_pricing = pricing[model]
        input_cost = (usage_stats["input_tokens"] / 1_000_000) * model_pricing["input"]
        output_cost = (usage_stats["output_tokens"] / 1_000_000) * model_pricing["output"]
        total_cost = input_cost + output_cost

        logger.info(f"[AI EDITOR] Cost: ${total_cost:.5f} ({usage_stats['input_tokens']} in, {usage_stats['output_tokens']} out)")

        return {
            "suggested_edit": result.get("suggested_edit", ""),
            "reasoning": result.get("reasoning", ""),
            "model_used": model,
            "complexity": complexity,
            "cost_estimate": round(total_cost, 6),
            "tokens": usage_stats
        }

    except Exception as e:
        logger.error(f"[AI EDITOR] Edit generation failed: {str(e)}")
        raise Exception(f"Failed to generate edit suggestion: {str(e)}")


async def generate_edit_suggestion_streaming(
    selected_text: str,
    instruction: str,
    section_context: str,
    full_report_summary: Optional[str] = None,
    complexity: Optional[str] = None
) -> AsyncIterator[str]:
    """
    Generate edit suggestion with streaming support

    Yields JSON chunks:
    - {"type": "status", "message": "Analyzing..."}
    - {"type": "chunk", "text": "partial edit text..."}
    - {"type": "complete", "suggested_edit": "...", "reasoning": "...", ...}
    """

    # Auto-detect complexity
    if complexity is None:
        complexity = classify_edit_complexity(instruction, selected_text)

    model = MODEL_SIMPLE if complexity == "simple" else MODEL_COMPLEX

    yield json.dumps({
        "type": "status",
        "message": f"Using {complexity} editing mode...",
        "model": model,
        "complexity": complexity
    }) + "\n"

    # Build prompt (same as non-streaming version)
    prompt = f"""You are an expert editor helping improve a strategic business report in Portuguese (Brazilian).

**SELECTED TEXT TO EDIT:**
"{selected_text}"

**SECTION CONTEXT:**
{section_context}

**USER INSTRUCTION:**
{instruction}

**YOUR TASK:**
1. Apply the user's instruction to the selected text
2. Keep the edit concise and focused on the selected text only
3. Maintain Brazilian Portuguese
4. Preserve any source citations (fonte:, baseado em, etc.)
5. Keep the same tone and professionalism as the original

**OUTPUT FORMAT (JSON ONLY):**
{{
  "suggested_edit": "Your edited version of the selected text",
  "reasoning": "Brief explanation of what you changed and why (1-2 sentences)"
}}

**CRITICAL:**
- Output ONLY valid JSON
- Do NOT change text outside the selected portion
- Keep source attributions intact
"""

    system_prompt = "You are an expert editor. Follow instructions precisely. Output JSON only."

    try:
        # Stream response
        full_response = ""
        async for chunk in call_llm_streaming(model, prompt, system_prompt):
            full_response += chunk
            yield json.dumps({
                "type": "chunk",
                "text": chunk
            }) + "\n"

        # Parse final result
        result = json.loads(full_response)

        yield json.dumps({
            "type": "complete",
            "suggested_edit": result.get("suggested_edit", ""),
            "reasoning": result.get("reasoning", ""),
            "model_used": model,
            "complexity": complexity
        }) + "\n"

    except Exception as e:
        logger.error(f"[AI EDITOR] Streaming edit failed: {str(e)}")
        yield json.dumps({
            "type": "error",
            "message": str(e)
        }) + "\n"


# ============================================================================
# JSON PATH EDITING
# ============================================================================

def apply_edit_to_json_path(
    report_json: Dict[str, Any],
    section_path: str,
    new_text: str
) -> Dict[str, Any]:
    """
    Apply edit to a specific path in the report JSON

    Args:
        report_json: Full report JSON
        section_path: Path to edit (e.g., "sumario_executivo" or "recomendacoes[0].titulo")
        new_text: New text to replace

    Returns:
        Updated report JSON

    Examples:
        section_path = "sumario_executivo" → report_json["sumario_executivo"] = new_text
        section_path = "recomendacoes[0].titulo" → report_json["recomendacoes"][0]["titulo"] = new_text
    """

    # Parse path (handle array indexing like "recomendacoes[0].titulo")
    path_parts = []
    current = ""

    for char in section_path:
        if char == '[':
            if current:
                path_parts.append(current)
                current = ""
        elif char == ']':
            if current:
                path_parts.append(int(current))
                current = ""
        elif char == '.':
            if current:
                path_parts.append(current)
                current = ""
        else:
            current += char

    if current:
        path_parts.append(current)

    # Navigate to parent
    current_obj = report_json
    for part in path_parts[:-1]:
        if isinstance(part, int):
            current_obj = current_obj[part]
        else:
            current_obj = current_obj[part]

    # Set final value
    final_key = path_parts[-1]
    current_obj[final_key] = new_text

    return report_json


# ============================================================================
# LLM CALLER (NON-STREAMING)
# ============================================================================

async def call_llm(
    model: str,
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> tuple[str, dict]:
    """
    Call LLM and return response + usage stats

    Returns:
        (content, usage_stats) where usage_stats = {"input_tokens": int, "output_tokens": int}
    """

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://strategy-ai.com",
        "X-Title": "Strategy AI - Report Editor",
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

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()

        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"].strip()

            # Clean markdown code blocks if present
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

            # Extract usage stats
            usage = data.get("usage", {})
            usage_stats = {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0)
            }

            return content, usage_stats
        else:
            raise Exception(f"Unexpected API response: {data}")


# ============================================================================
# LLM CALLER (STREAMING)
# ============================================================================

async def call_llm_streaming(
    model: str,
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> AsyncIterator[str]:
    """
    Call LLM with streaming support

    Yields text chunks as they arrive
    """

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://strategy-ai.com",
        "X-Title": "Strategy AI - Report Editor",
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
        "stream": True
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async with client.stream("POST", OPENROUTER_URL, headers=headers, json=payload) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix

                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue


# ============================================================================
# UTILITY: EXTRACT SECTION CONTEXT
# ============================================================================

def extract_section_context(
    full_report: Dict[str, Any],
    section_path: str,
    context_chars: int = 500
) -> str:
    """
    Extract surrounding context for a section to help AI understand placement

    Args:
        full_report: Full report JSON
        section_path: Path being edited
        context_chars: How many characters of context to include

    Returns:
        Context string
    """

    try:
        # Get the section being edited
        path_parts = section_path.replace('[', '.').replace(']', '').split('.')
        section = full_report
        for part in path_parts:
            if part.isdigit():
                section = section[int(part)]
            else:
                section = section[part]

        # Convert section to string
        if isinstance(section, str):
            section_text = section
        else:
            section_text = json.dumps(section, ensure_ascii=False, indent=2)

        # Get surrounding context (simplified - just return the section for now)
        if len(section_text) > context_chars:
            return section_text[:context_chars] + "..."
        else:
            return section_text

    except Exception as e:
        logger.warning(f"[AI EDITOR] Could not extract context: {str(e)}")
        return ""
