#!/usr/bin/env python3
"""
Simple OpenAPI Documentation Checker

This script performs static analysis on the route files to check
documentation completeness without requiring dependencies.

Usage:
    python scripts/check_docs.py
"""
import re
from pathlib import Path
from typing import List, Dict, Tuple


def check_route_file(file_path: Path) -> Dict:
    """
    Check a single route file for documentation.

    Returns:
        Dictionary with analysis results
    """
    content = file_path.read_text(encoding='utf-8')

    # Find all route decorators
    route_pattern = r'@router\.(get|post|put|patch|delete)\('
    routes = re.findall(route_pattern, content, re.MULTILINE)

    # Find routes with summary parameter
    summary_pattern = r'@router\.(get|post|put|patch|delete)\([^)]*summary='
    routes_with_summary = re.findall(summary_pattern, content, re.MULTILINE | re.DOTALL)

    # Find routes with description parameter
    description_pattern = r'@router\.(get|post|put|patch|delete)\([^)]*description='
    routes_with_description = re.findall(description_pattern, content, re.MULTILINE | re.DOTALL)

    # Find routes with responses parameter
    responses_pattern = r'@router\.(get|post|put|patch|delete)\([^)]*responses='
    routes_with_responses = re.findall(responses_pattern, content, re.MULTILINE | re.DOTALL)

    return {
        'file': file_path.name,
        'total_routes': len(routes),
        'with_summary': len(routes_with_summary),
        'with_description': len(routes_with_description),
        'with_responses': len(routes_with_responses)
    }


def main():
    """Main checker function"""
    print("\n" + "="*70)
    print("  Strategy AI - OpenAPI Documentation Check")
    print("="*70 + "\n")

    # Find all route files
    routes_dir = Path(__file__).parent.parent / "app" / "routes"

    if not routes_dir.exists():
        print(f"Error: Routes directory not found: {routes_dir}")
        return

    route_files = list(routes_dir.glob("*.py"))
    route_files = [f for f in route_files if f.name != "__init__.py"]

    print(f"Found {len(route_files)} route files\n")

    all_results = []
    total_routes = 0
    total_with_summary = 0
    total_with_description = 0
    total_with_responses = 0

    # Check each file
    for file_path in sorted(route_files):
        result = check_route_file(file_path)
        all_results.append(result)

        total_routes += result['total_routes']
        total_with_summary += result['with_summary']
        total_with_description += result['with_description']
        total_with_responses += result['with_responses']

        # Print file results
        print(f"File: {result['file']}")
        print(f"  Routes: {result['total_routes']}")
        print(f"  With summary: {result['with_summary']}/{result['total_routes']}")
        print(f"  With description: {result['with_description']}/{result['total_routes']}")
        print(f"  With responses: {result['with_responses']}/{result['total_routes']}")

        # Coverage percentage
        if result['total_routes'] > 0:
            summary_pct = (result['with_summary'] / result['total_routes']) * 100
            desc_pct = (result['with_description'] / result['total_routes']) * 100
            resp_pct = (result['with_responses'] / result['total_routes']) * 100

            print(f"  Coverage: Summary {summary_pct:.0f}%, Description {desc_pct:.0f}%, Responses {resp_pct:.0f}%")
        print()

    # Overall statistics
    print("="*70)
    print("OVERALL STATISTICS")
    print("="*70 + "\n")

    print(f"Total routes analyzed: {total_routes}")
    print(f"Routes with summary: {total_with_summary}/{total_routes} ({(total_with_summary/total_routes*100):.1f}%)")
    print(f"Routes with description: {total_with_description}/{total_routes} ({(total_with_description/total_routes*100):.1f}%)")
    print(f"Routes with responses: {total_with_responses}/{total_routes} ({(total_with_responses/total_routes*100):.1f}%)")

    # Overall coverage
    summary_coverage = (total_with_summary / total_routes * 100) if total_routes > 0 else 0
    desc_coverage = (total_with_description / total_routes * 100) if total_routes > 0 else 0
    resp_coverage = (total_with_responses / total_routes * 100) if total_routes > 0 else 0

    avg_coverage = (summary_coverage + desc_coverage + resp_coverage) / 3

    print(f"\nAverage documentation coverage: {avg_coverage:.1f}%")

    if avg_coverage >= 80:
        status = "EXCELLENT"
        symbol = "+"
    elif avg_coverage >= 60:
        status = "GOOD"
        symbol = "+"
    elif avg_coverage >= 40:
        status = "MODERATE"
        symbol = "~"
    else:
        status = "NEEDS IMPROVEMENT"
        symbol = "-"

    print(f"\nDocumentation Status: {status} [{symbol}]")

    # Check main.py for app configuration
    print("\n" + "="*70)
    print("APP CONFIGURATION CHECK")
    print("="*70 + "\n")

    main_file = Path(__file__).parent.parent / "app" / "main.py"
    if main_file.exists():
        main_content = main_file.read_text(encoding='utf-8')

        checks = {
            'title': 'title=' in main_content,
            'description': 'description=' in main_content and len(main_content) > 1000,
            'version': 'version=' in main_content,
            'contact': 'contact=' in main_content,
            'license_info': 'license_info=' in main_content,
            'servers': 'servers=' in main_content,
            'openapi_tags': 'openapi_tags=' in main_content
        }

        for key, value in checks.items():
            status = "[+]" if value else "[ ]"
            print(f"{status} {key.replace('_', ' ').title()}")

        configured = sum(checks.values())
        total_checks = len(checks)
        print(f"\nApp configuration: {configured}/{total_checks} items configured ({configured/total_checks*100:.0f}%)")

    # Check if openapi.py exists
    print("\n" + "="*70)
    print("CUSTOM OPENAPI MODULE CHECK")
    print("="*70 + "\n")

    openapi_file = Path(__file__).parent.parent / "app" / "core" / "openapi.py"
    if openapi_file.exists():
        print("[+] app/core/openapi.py exists")

        openapi_content = openapi_file.read_text(encoding='utf-8')
        features = {
            'custom_openapi function': 'def custom_openapi' in openapi_content,
            'EXAMPLES': 'EXAMPLES = {' in openapi_content,
            'ERROR_RESPONSES': 'ERROR_RESPONSES = {' in openapi_content,
            'SECURITY_SCHEMES': 'SECURITY_SCHEMES = {' in openapi_content,
        }

        for key, value in features.items():
            status = "[+]" if value else "[ ]"
            print(f"{status} {key}")
    else:
        print("[ ] app/core/openapi.py not found")

    print("\n" + "="*70)
    print("Documentation check complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
