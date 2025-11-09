#!/usr/bin/env python3
"""
API Documentation Generator Script

This script generates comprehensive API documentation in multiple formats:
- OpenAPI JSON schema
- OpenAPI YAML schema
- Markdown documentation
- Postman collection (JSON)

Usage:
    python scripts/generate_docs.py [--output-dir docs] [--formats all]

Options:
    --output-dir    Output directory for generated files (default: docs/)
    --formats       Comma-separated list: json,yaml,markdown,postman (default: all)
    --host          API host URL for examples (default: http://localhost:8000)
"""
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.core.openapi import custom_openapi


def generate_openapi_json(output_dir: Path, host: str) -> str:
    """
    Generate OpenAPI JSON schema file.

    Args:
        output_dir: Output directory path
        host: API host URL

    Returns:
        Path to generated file
    """
    schema = custom_openapi(app)

    # Update servers with provided host
    schema["servers"] = [
        {"url": host, "description": "API Server"}
    ]

    output_file = output_dir / "openapi.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated OpenAPI JSON: {output_file}")
    return str(output_file)


def generate_openapi_yaml(output_dir: Path, host: str) -> str:
    """
    Generate OpenAPI YAML schema file.

    Args:
        output_dir: Output directory path
        host: API host URL

    Returns:
        Path to generated file
    """
    try:
        import yaml
    except ImportError:
        print("⚠️  PyYAML not installed. Skipping YAML generation.")
        print("   Install with: pip install pyyaml")
        return None

    schema = custom_openapi(app)

    # Update servers with provided host
    schema["servers"] = [
        {"url": host, "description": "API Server"}
    ]

    output_file = output_dir / "openapi.yaml"
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(schema, f, default_flow_style=False, allow_unicode=True)

    print(f"✅ Generated OpenAPI YAML: {output_file}")
    return str(output_file)


def generate_markdown_docs(output_dir: Path, host: str) -> str:
    """
    Generate comprehensive Markdown documentation.

    Args:
        output_dir: Output directory path
        host: API host URL

    Returns:
        Path to generated file
    """
    schema = custom_openapi(app)

    output_file = output_dir / "API_DOCUMENTATION.md"

    with open(output_file, "w", encoding="utf-8") as f:
        # Header
        f.write(f"# {schema['info']['title']}\n\n")
        f.write(f"**Version:** {schema['info']['version']}  \n")
        f.write(f"**Base URL:** `{host}`  \n")
        f.write(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")

        # Description
        f.write("## Overview\n\n")
        f.write(f"{schema['info']['description']}\n\n")

        # Contact & License
        if 'contact' in schema['info']:
            contact = schema['info']['contact']
            f.write("## Contact\n\n")
            f.write(f"- **Name:** {contact.get('name', 'N/A')}\n")
            f.write(f"- **Email:** {contact.get('email', 'N/A')}\n")
            f.write(f"- **URL:** {contact.get('url', 'N/A')}\n\n")

        if 'license' in schema['info']:
            license_info = schema['info']['license']
            f.write("## License\n\n")
            f.write(f"{license_info.get('name', 'N/A')} - [View License]({license_info.get('url', '#')})\n\n")

        # Authentication
        f.write("## Authentication\n\n")
        f.write("This API uses Bearer token authentication (JWT).\n\n")
        f.write("**How to authenticate:**\n\n")
        f.write("1. Obtain a token via `POST /api/auth/login`\n")
        f.write("2. Include the token in the `Authorization` header:\n\n")
        f.write("```\nAuthorization: Bearer <your_token>\n```\n\n")

        # Endpoints by tag
        f.write("## Endpoints\n\n")

        # Group paths by tags
        paths_by_tag: Dict[str, List] = {}
        for path, methods in schema['paths'].items():
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'patch', 'delete']:
                    tags = details.get('tags', ['default'])
                    tag = tags[0] if tags else 'default'

                    if tag not in paths_by_tag:
                        paths_by_tag[tag] = []

                    paths_by_tag[tag].append({
                        'path': path,
                        'method': method.upper(),
                        'summary': details.get('summary', 'No summary'),
                        'description': details.get('description', ''),
                        'responses': details.get('responses', {}),
                        'security': details.get('security', [])
                    })

        # Write endpoints by tag
        for tag in sorted(paths_by_tag.keys()):
            # Get tag description from openapi_tags
            tag_desc = ""
            for tag_info in schema.get('tags', []):
                if tag_info['name'] == tag:
                    tag_desc = tag_info.get('description', '')
                    break

            f.write(f"### {tag.title()}\n\n")
            if tag_desc:
                f.write(f"{tag_desc}\n\n")

            for endpoint in paths_by_tag[tag]:
                # Endpoint header
                f.write(f"#### `{endpoint['method']}` {endpoint['path']}\n\n")
                f.write(f"**{endpoint['summary']}**\n\n")

                # Authentication indicator
                if endpoint['security']:
                    f.write("🔒 *Requires authentication*\n\n")

                # Description
                if endpoint['description']:
                    f.write(f"{endpoint['description']}\n\n")

                # Response codes
                f.write("**Responses:**\n\n")
                for code, response in endpoint['responses'].items():
                    f.write(f"- `{code}`: {response.get('description', 'No description')}\n")
                f.write("\n")

                # cURL example
                f.write("**Example Request:**\n\n")
                f.write("```bash\n")
                auth_header = "-H \"Authorization: Bearer <token>\" \\\n  " if endpoint['security'] else ""
                f.write(f"curl -X {endpoint['method']} {host}{endpoint['path']} \\\n  ")
                if auth_header:
                    f.write(auth_header)
                f.write("-H \"Content-Type: application/json\"\n")
                f.write("```\n\n")

                f.write("---\n\n")

        # Rate Limiting
        f.write("## Rate Limiting\n\n")
        f.write("The API implements rate limiting to ensure fair usage:\n\n")
        f.write("- **Public endpoints:** 3 submissions per IP per day\n")
        f.write("- **Authenticated endpoints:** 100 requests per minute\n\n")
        f.write("Rate limit headers are included in responses:\n\n")
        f.write("```\nX-RateLimit-Limit: 100\n")
        f.write("X-RateLimit-Remaining: 95\n")
        f.write("X-RateLimit-Reset: 1640000000\n```\n\n")

        # Error Handling
        f.write("## Error Handling\n\n")
        f.write("All errors follow a consistent format:\n\n")
        f.write("```json\n")
        f.write("{\n")
        f.write('  "success": false,\n')
        f.write('  "error": "Error message description"\n')
        f.write("}\n")
        f.write("```\n\n")

        # Common status codes
        f.write("**Common Status Codes:**\n\n")
        f.write("- `200`: Success\n")
        f.write("- `400`: Bad Request - Invalid input\n")
        f.write("- `401`: Unauthorized - Invalid or missing token\n")
        f.write("- `403`: Forbidden - Insufficient permissions\n")
        f.write("- `404`: Not Found - Resource doesn't exist\n")
        f.write("- `429`: Too Many Requests - Rate limit exceeded\n")
        f.write("- `500`: Internal Server Error\n")
        f.write("- `503`: Service Unavailable - Dependency failure\n\n")

        # Footer
        f.write("---\n\n")
        f.write(f"*Documentation generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*\n")

    print(f"✅ Generated Markdown documentation: {output_file}")
    return str(output_file)


def generate_postman_collection(output_dir: Path, host: str) -> str:
    """
    Generate Postman collection JSON.

    Args:
        output_dir: Output directory path
        host: API host URL

    Returns:
        Path to generated file
    """
    schema = custom_openapi(app)

    collection = {
        "info": {
            "name": schema['info']['title'],
            "description": schema['info']['description'],
            "version": schema['info']['version'],
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "auth": {
            "type": "bearer",
            "bearer": [
                {
                    "key": "token",
                    "value": "{{jwt_token}}",
                    "type": "string"
                }
            ]
        },
        "variable": [
            {
                "key": "base_url",
                "value": host,
                "type": "string"
            },
            {
                "key": "jwt_token",
                "value": "",
                "type": "string"
            }
        ],
        "item": []
    }

    # Group endpoints by tag
    folders: Dict[str, List] = {}
    for path, methods in schema['paths'].items():
        for method, details in methods.items():
            if method in ['get', 'post', 'put', 'patch', 'delete']:
                tags = details.get('tags', ['default'])
                tag = tags[0] if tags else 'default'

                if tag not in folders:
                    folders[tag] = []

                # Build request
                request = {
                    "name": details.get('summary', path),
                    "request": {
                        "method": method.upper(),
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "url": {
                            "raw": f"{{{{base_url}}}}{path}",
                            "host": ["{{base_url}}"],
                            "path": path.strip('/').split('/')
                        },
                        "description": details.get('description', '')
                    }
                }

                # Add auth if required
                if details.get('security'):
                    request["request"]["auth"] = {
                        "type": "bearer",
                        "bearer": [
                            {
                                "key": "token",
                                "value": "{{jwt_token}}",
                                "type": "string"
                            }
                        ]
                    }

                # Add body for POST/PUT/PATCH
                if method in ['post', 'put', 'patch']:
                    request["request"]["body"] = {
                        "mode": "raw",
                        "raw": "{\n  \n}",
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    }

                folders[tag].append(request)

    # Add folders to collection
    for tag, items in sorted(folders.items()):
        collection['item'].append({
            "name": tag.title(),
            "item": items
        })

    output_file = output_dir / "postman_collection.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated Postman collection: {output_file}")
    return str(output_file)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Generate API documentation in multiple formats"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs",
        help="Output directory for generated files (default: docs/)"
    )
    parser.add_argument(
        "--formats",
        type=str,
        default="all",
        help="Comma-separated list: json,yaml,markdown,postman (default: all)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost:8000",
        help="API host URL for examples (default: http://localhost:8000)"
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parse formats
    formats = args.formats.lower().split(',') if args.formats != 'all' else ['json', 'yaml', 'markdown', 'postman']

    print(f"\n{'='*60}")
    print(f"  Strategy AI API Documentation Generator")
    print(f"{'='*60}\n")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"API host: {args.host}")
    print(f"Formats: {', '.join(formats)}\n")

    generated_files = []

    # Generate requested formats
    if 'json' in formats:
        file_path = generate_openapi_json(output_dir, args.host)
        if file_path:
            generated_files.append(file_path)

    if 'yaml' in formats:
        file_path = generate_openapi_yaml(output_dir, args.host)
        if file_path:
            generated_files.append(file_path)

    if 'markdown' in formats:
        file_path = generate_markdown_docs(output_dir, args.host)
        if file_path:
            generated_files.append(file_path)

    if 'postman' in formats:
        file_path = generate_postman_collection(output_dir, args.host)
        if file_path:
            generated_files.append(file_path)

    print(f"\n{'='*60}")
    print(f"  Documentation generation complete!")
    print(f"{'='*60}\n")
    print(f"Generated {len(generated_files)} file(s):\n")
    for file_path in generated_files:
        print(f"  • {file_path}")
    print()


if __name__ == "__main__":
    main()
