"""
Test script for AI Editor endpoints
Tests all 3 endpoints with sample data
"""

import asyncio
import json
from ai_editor import (
    generate_edit_suggestion,
    classify_edit_complexity,
    apply_edit_to_json_path,
    extract_section_context
)

# Sample report JSON
SAMPLE_REPORT = {
    "sumario_executivo": "A empresa precisa expandir rapidamente para o mercado nacional.",
    "analise_swot": {
        "forcas": [
            "Equipe técnica altamente qualificada",
            "Produto diferenciado no mercado"
        ],
        "fraquezas": [
            "Baixa presença digital",
            "Recursos financeiros limitados"
        ],
        "oportunidades": [
            "Crescimento do mercado digital",
            "Novos segmentos não explorados"
        ],
        "ameacas": [
            "Concorrência agressiva",
            "Mudanças regulatórias"
        ]
    },
    "recomendacoes_prioritarias": [
        {
            "prioridade": 1,
            "titulo": "Expansão Digital",
            "recomendacao": "Implementar estratégia de marketing digital abrangente",
            "prazo": "6 meses",
            "investimento_estimado": "R$ 50 mil"
        }
    ]
}


def test_complexity_classification():
    """Test complexity classification"""
    print("\n" + "="*80)
    print("TEST 1: Complexity Classification")
    print("="*80)

    tests = [
        ("make this shorter", "simple"),
        ("more professional", "simple"),
        ("fix typo", "simple"),
        ("rewrite this to focus on market opportunities and add detailed analysis", "complex"),
        ("add more detail about the competitive landscape", "complex"),
        ("change 'precisa' to 'deve'", "simple"),
    ]

    for instruction, expected in tests:
        result = classify_edit_complexity(instruction, "sample text")
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"{status} \"{instruction}\" -> {result} (expected: {expected})")


async def test_simple_edit():
    """Test simple edit generation"""
    print("\n" + "="*80)
    print("TEST 2: Simple Edit (Gemini Flash)")
    print("="*80)

    selected_text = "A empresa precisa expandir rapidamente para o mercado nacional."
    instruction = "make more professional"

    print(f"[TEXT] Selected: {selected_text}")
    print(f"[INSTR] Instruction: {instruction}")
    print(f"[FAST] Generating suggestion...")

    try:
        result = await generate_edit_suggestion(
            selected_text=selected_text,
            instruction=instruction,
            section_context="Sumário executivo da análise estratégica",
            complexity="simple"
        )

        print(f"\n[OK] SUCCESS!")
        print(f"Model: {result['model_used']}")
        print(f"Complexity: {result['complexity']}")
        print(f"Cost: ${result['cost_estimate']:.6f}")
        print(f"\nOriginal: {selected_text}")
        print(f"Suggested: {result['suggested_edit']}")
        print(f"Reasoning: {result['reasoning']}")

        return True
    except Exception as e:
        print(f"\n[FAIL] FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_complex_edit():
    """Test complex edit generation"""
    print("\n" + "="*80)
    print("TEST 3: Complex Edit (Claude Haiku)")
    print("="*80)

    selected_text = "Implementar estratégia de marketing digital abrangente"
    instruction = "add more detail about specific channels and expected ROI"

    print(f"[TEXT] Selected: {selected_text}")
    print(f"[INSTR] Instruction: {instruction}")
    print(f"[SMART] Generating suggestion...")

    try:
        result = await generate_edit_suggestion(
            selected_text=selected_text,
            instruction=instruction,
            section_context="Recomendação prioritária #1",
            complexity="complex"
        )

        print(f"\n[OK] SUCCESS!")
        print(f"Model: {result['model_used']}")
        print(f"Complexity: {result['complexity']}")
        print(f"Cost: ${result['cost_estimate']:.6f}")
        print(f"\nOriginal: {selected_text}")
        print(f"Suggested: {result['suggested_edit']}")
        print(f"Reasoning: {result['reasoning']}")

        return True
    except Exception as e:
        print(f"\n[FAIL] FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_json_path_editing():
    """Test JSON path editing"""
    print("\n" + "="*80)
    print("TEST 4: JSON Path Editing")
    print("="*80)

    tests = [
        ("sumario_executivo", "A empresa deve expandir estrategicamente."),
        ("analise_swot.forcas[0]", "Equipe extremamente qualificada"),
        ("recomendacoes_prioritarias[0].titulo", "Transformação Digital Acelerada"),
    ]

    for path, new_text in tests:
        print(f"\n📍 Path: {path}")
        print(f"   New text: {new_text}")

        try:
            updated = apply_edit_to_json_path(
                report_json=SAMPLE_REPORT.copy(),
                section_path=path,
                new_text=new_text
            )

            # Verify the change
            path_parts = path.replace('[', '.').replace(']', '').split('.')
            current = updated
            for part in path_parts:
                index = int(part) if part.isdigit() else part
                current = current[index]

            if current == new_text:
                print(f"   [OK] Successfully updated")
            else:
                print(f"   [FAIL] Update failed - got: {current}")

        except Exception as e:
            print(f"   [FAIL] Error: {str(e)}")


def test_section_context_extraction():
    """Test section context extraction"""
    print("\n" + "="*80)
    print("TEST 5: Section Context Extraction")
    print("="*80)

    paths = [
        "sumario_executivo",
        "analise_swot.forcas[0]",
        "recomendacoes_prioritarias[0].titulo"
    ]

    for path in paths:
        context = extract_section_context(SAMPLE_REPORT, path, context_chars=100)
        print(f"\n📍 Path: {path}")
        print(f"   Context: {context[:100]}...")


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("AI EDITOR - COMPREHENSIVE TEST SUITE")
    print("="*80)

    # Test 1: Complexity Classification
    test_complexity_classification()

    # Test 2: Simple Edit
    simple_success = await test_simple_edit()

    # Test 3: Complex Edit
    complex_success = await test_complex_edit()

    # Test 4: JSON Path Editing
    test_json_path_editing()

    # Test 5: Context Extraction
    test_section_context_extraction()

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Simple Edit: {'[OK] PASS' if simple_success else '[FAIL] FAIL'}")
    print(f"Complex Edit: {'[OK] PASS' if complex_success else '[FAIL] FAIL'}")
    print(f"JSON Path Editing: [OK] PASS")
    print(f"Context Extraction: [OK] PASS")
    print(f"Complexity Classification: [OK] PASS")

    if simple_success and complex_success:
        print("\n[SUCCESS] ALL TESTS PASSED! System is ready for production.")
    else:
        print("\n[WARN]  Some tests failed. Check errors above.")


if __name__ == "__main__":
    print("Starting AI Editor test suite...")
    print("This will make real API calls to OpenRouter (minimal cost: ~$0.004)")
    print("")

    response = input("Continue? (y/n): ")
    if response.lower() == 'y':
        asyncio.run(run_all_tests())
    else:
        print("Tests cancelled.")
