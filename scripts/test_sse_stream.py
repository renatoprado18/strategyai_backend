#!/usr/bin/env python3
"""
Test Progressive Enrichment SSE Stream

Tests the actual SSE stream on Railway to verify what field names
are being sent in the events.

Usage:
    python scripts/test_sse_stream.py https://your-railway-app.railway.app https://example.com
"""

import sys
import json
import time
import requests
from typing import Optional


def start_enrichment(base_url: str, website_url: str) -> Optional[str]:
    """
    Start progressive enrichment and get session ID.

    Args:
        base_url: Base URL of the API (e.g., https://your-app.railway.app)
        website_url: Website to enrich (e.g., https://example.com)

    Returns:
        Session ID or None if failed
    """
    url = f"{base_url}/api/enrichment/progressive/start"
    payload = {
        "website_url": website_url,
        "user_email": "test@example.com"
    }

    print(f"\n📡 Starting progressive enrichment for: {website_url}")
    print(f"   POST {url}")

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        data = response.json()
        session_id = data.get("session_id")

        print(f"✅ Enrichment started!")
        print(f"   Session ID: {session_id}")
        print(f"   Stream URL: {data.get('stream_url')}")

        return session_id

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to start enrichment: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   Response: {e.response.text}")
        return None


def test_sse_stream(base_url: str, session_id: str):
    """
    Connect to SSE stream and log all events with field analysis.

    Args:
        base_url: Base URL of the API
        session_id: Session ID from start_enrichment
    """
    url = f"{base_url}/api/enrichment/progressive/stream/{session_id}"

    print(f"\n🔌 Connecting to SSE stream...")
    print(f"   GET {url}")
    print(f"   Waiting for events...\n")

    try:
        # Connect to SSE stream
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        # Process SSE events
        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode("utf-8")

            # Parse SSE event format
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
                print(f"\n📨 Event Type: {event_type}")

            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()

                try:
                    data = json.loads(data_str)

                    # Analyze fields
                    if "fields" in data:
                        fields = data["fields"]
                        confidence_scores = data.get("confidence_scores", {})

                        print(f"\n   📊 Fields Extracted ({len(fields)} total):")

                        # Check for field name issues
                        has_company_name = "company_name" in fields
                        has_business_name = "business_name" in fields
                        has_name = "name" in fields
                        has_city = "city" in fields

                        # Print all fields with confidence
                        for field_name, field_value in fields.items():
                            confidence = confidence_scores.get(field_name, 0)

                            # Highlight problematic field names
                            if field_name in ["company_name", "business_name"]:
                                print(f"   ⚠️  {field_name}: {field_value} (confidence: {confidence:.1f}%)")
                                print(f"       ↑ Should be 'name' not '{field_name}'!")
                            else:
                                print(f"   ✓  {field_name}: {field_value} (confidence: {confidence:.1f}%)")

                        # Summary
                        print(f"\n   🔍 Field Name Analysis:")
                        if has_company_name:
                            print(f"   ❌ Found 'company_name' - frontend expects 'name'")
                        if has_business_name:
                            print(f"   ❌ Found 'business_name' - frontend expects 'name'")
                        if has_name:
                            print(f"   ✅ Found 'name' - correct!")
                        else:
                            print(f"   ❌ Missing 'name' field - form won't auto-fill!")

                        if has_city:
                            print(f"   ✅ Found 'city' - correct!")
                        else:
                            print(f"   ⚠️  Missing 'city' field")

                    # Print full JSON for debugging
                    print(f"\n   📄 Full Event Data:")
                    print(f"   {json.dumps(data, indent=2)}")

                except json.JSONDecodeError:
                    print(f"   Data: {data_str}")

                # Check if we're done
                if data.get("status") == "complete":
                    print(f"\n✅ Enrichment complete!")
                    break

    except requests.exceptions.RequestException as e:
        print(f"\n❌ SSE stream error: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   Response: {e.response.text}")


def main():
    """Main test function"""
    if len(sys.argv) < 3:
        print("Usage: python scripts/test_sse_stream.py <base_url> <website_url>")
        print("Example: python scripts/test_sse_stream.py https://your-app.railway.app https://example.com")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    website_url = sys.argv[2]

    print("=" * 80)
    print("Progressive Enrichment SSE Stream Test")
    print("=" * 80)

    # Step 1: Start enrichment
    session_id = start_enrichment(base_url, website_url)
    if not session_id:
        print("\n❌ Failed to start enrichment. Exiting.")
        sys.exit(1)

    # Step 2: Test SSE stream
    time.sleep(1)  # Give backend a moment to process
    test_sse_stream(base_url, session_id)

    print("\n" + "=" * 80)
    print("Test complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
