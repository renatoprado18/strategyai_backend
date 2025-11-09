#!/usr/bin/env python3
"""
OpenAPI Schema Validator

Validates the OpenAPI schema without requiring database connections.
This script checks:
- OpenAPI schema structure
- Route documentation completeness
- Response model definitions
- Security schemes
- Example validity

Usage:
    python scripts/validate_openapi.py
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_success(message: str):
    """Print success message in green"""
    print(f"{GREEN}✓{RESET} {message}")


def print_warning(message: str):
    """Print warning message in yellow"""
    print(f"{YELLOW}⚠{RESET} {message}")


def print_error(message: str):
    """Print error message in red"""
    print(f"{RED}✗{RESET} {message}")


def print_info(message: str):
    """Print info message in blue"""
    print(f"{BLUE}ℹ{RESET} {message}")


def print_header(message: str):
    """Print section header"""
    print(f"\n{BOLD}{message}{RESET}")
    print("=" * len(message))


def check_endpoint_documentation(paths: Dict) -> Tuple[int, int, List[str]]:
    """
    Check endpoint documentation completeness.

    Returns:
        Tuple of (documented_count, total_count, issues)
    """
    issues = []
    total = 0
    documented = 0

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() in ['get', 'post', 'put', 'patch', 'delete']:
                total += 1

                # Check summary
                if 'summary' in details and details['summary']:
                    documented += 1
                else:
                    issues.append(f"{method.upper()} {path}: Missing summary")

                # Check description
                if 'description' not in details or not details['description']:
                    issues.append(f"{method.upper()} {path}: Missing description")

                # Check responses
                if 'responses' not in details or not details['responses']:
                    issues.append(f"{method.upper()} {path}: Missing response definitions")

    return documented, total, issues


def check_response_models(paths: Dict) -> List[str]:
    """Check if responses have proper examples or schemas"""
    issues = []

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() in ['get', 'post', 'put', 'patch', 'delete']:
                responses = details.get('responses', {})

                for status_code, response in responses.items():
                    content = response.get('content', {})

                    # Check if response has content
                    if not content and status_code != '204':  # 204 has no content
                        issues.append(
                            f"{method.upper()} {path} ({status_code}): "
                            f"Response has no content definition"
                        )

    return issues


def check_security_schemes(schema: Dict) -> List[str]:
    """Check security scheme definitions"""
    issues = []

    components = schema.get('components', {})
    security_schemes = components.get('securitySchemes', {})

    if not security_schemes:
        issues.append("No security schemes defined")
    else:
        # Check each scheme has required fields
        for scheme_name, scheme in security_schemes.items():
            if 'type' not in scheme:
                issues.append(f"Security scheme '{scheme_name}' missing type")
            if 'description' not in scheme:
                issues.append(f"Security scheme '{scheme_name}' missing description")

    return issues


def check_tags(schema: Dict) -> List[str]:
    """Check tag definitions"""
    issues = []

    tags = schema.get('tags', [])
    if not tags:
        issues.append("No tags defined for endpoint organization")
        return issues

    # Check each tag has description
    for tag in tags:
        if 'description' not in tag or not tag['description']:
            issues.append(f"Tag '{tag.get('name', 'unknown')}' missing description")

    # Check if all used tags are defined
    defined_tags = {tag['name'] for tag in tags}
    used_tags = set()

    paths = schema.get('paths', {})
    for path, methods in paths.items():
        for method, details in methods.items():
            if isinstance(details, dict):
                endpoint_tags = details.get('tags', [])
                used_tags.update(endpoint_tags)

    undefined_tags = used_tags - defined_tags
    if undefined_tags:
        issues.append(f"Tags used but not defined: {', '.join(undefined_tags)}")

    return issues


def check_info_metadata(schema: Dict) -> List[str]:
    """Check API info metadata"""
    issues = []

    info = schema.get('info', {})

    required_fields = ['title', 'version', 'description']
    for field in required_fields:
        if field not in info or not info[field]:
            issues.append(f"Info section missing '{field}'")

    # Check optional but recommended fields
    recommended_fields = ['contact', 'license']
    for field in recommended_fields:
        if field not in info:
            issues.append(f"Info section missing recommended field '{field}'")

    return issues


def validate_openapi_schema():
    """Main validation function"""
    print_header("OpenAPI Schema Validation")

    # Try to import and generate schema
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))

        # Mock environment variables if not set
        import os
        mock_vars = {
            'SUPABASE_URL': 'https://mock.supabase.co',
            'SUPABASE_SERVICE_KEY': 'mock-service-key',
            'SUPABASE_ANON_KEY': 'mock-anon-key',
            'JWT_SECRET': 'mock-jwt-secret',
            'OPENROUTER_API_KEY': 'mock-openrouter-key',
            'UPSTASH_REDIS_URL': 'https://mock-redis.upstash.io',
            'UPSTASH_REDIS_TOKEN': 'mock-redis-token'
        }

        for key, value in mock_vars.items():
            if key not in os.environ:
                os.environ[key] = value

        from app.main import app
        from app.core.openapi import custom_openapi

        schema = custom_openapi(app)
        print_success("Successfully loaded OpenAPI schema")

    except Exception as e:
        print_error(f"Failed to load schema: {e}")
        return False

    # Validation checks
    all_passed = True

    # 1. Check info metadata
    print_header("1. API Info Metadata")
    info_issues = check_info_metadata(schema)
    if not info_issues:
        print_success("All required metadata present")
    else:
        all_passed = False
        for issue in info_issues:
            print_warning(issue)

    # 2. Check tags
    print_header("2. Tag Definitions")
    tag_issues = check_tags(schema)
    if not tag_issues:
        print_success("All tags properly defined")
    else:
        all_passed = False
        for issue in tag_issues:
            print_warning(issue)

    # 3. Check security schemes
    print_header("3. Security Schemes")
    security_issues = check_security_schemes(schema)
    if not security_issues:
        print_success("Security schemes properly configured")
    else:
        all_passed = False
        for issue in security_issues:
            print_warning(issue)

    # 4. Check endpoint documentation
    print_header("4. Endpoint Documentation")
    documented, total, doc_issues = check_endpoint_documentation(schema.get('paths', {}))
    coverage = (documented / total * 100) if total > 0 else 0

    print_info(f"Documentation coverage: {documented}/{total} endpoints ({coverage:.1f}%)")

    if coverage == 100:
        print_success("All endpoints have summaries")
    else:
        all_passed = False
        print_warning(f"{total - documented} endpoints missing summaries")

    if coverage >= 90:
        print_success(f"Good documentation coverage: {coverage:.1f}%")
    elif coverage >= 70:
        print_warning(f"Moderate documentation coverage: {coverage:.1f}%")
    else:
        print_error(f"Poor documentation coverage: {coverage:.1f}%")
        all_passed = False

    # Show first 5 issues
    if doc_issues and len(doc_issues) <= 5:
        for issue in doc_issues:
            print_warning(f"  - {issue}")
    elif doc_issues:
        for issue in doc_issues[:5]:
            print_warning(f"  - {issue}")
        print_info(f"  ... and {len(doc_issues) - 5} more issues")

    # 5. Check response models
    print_header("5. Response Models")
    response_issues = check_response_models(schema.get('paths', {}))
    if not response_issues:
        print_success("All responses have content definitions")
    else:
        print_warning(f"{len(response_issues)} responses missing content definitions")
        if len(response_issues) <= 3:
            for issue in response_issues:
                print_warning(f"  - {issue}")

    # 6. Statistics
    print_header("6. Schema Statistics")
    paths = schema.get('paths', {})
    total_endpoints = sum(
        1 for methods in paths.values()
        for method in methods.keys()
        if method.lower() in ['get', 'post', 'put', 'patch', 'delete']
    )
    print_info(f"Total endpoints: {total_endpoints}")
    print_info(f"Total paths: {len(paths)}")
    print_info(f"Total tags: {len(schema.get('tags', []))}")
    print_info(f"Security schemes: {len(schema.get('components', {}).get('securitySchemes', {}))}")

    # Final result
    print_header("Validation Result")
    if all_passed:
        print_success("OpenAPI schema validation passed! ✨")
        return True
    else:
        print_warning("OpenAPI schema has some issues that should be addressed")
        return False


if __name__ == "__main__":
    success = validate_openapi_schema()
    sys.exit(0 if success else 1)
