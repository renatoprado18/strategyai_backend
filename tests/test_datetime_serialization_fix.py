"""
Test datetime JSON serialization fix for cache system.

This test verifies that the cache system properly serializes datetime
objects to ISO format strings before storing in Supabase.

Created: 2025-01-10
"""

import json
from datetime import datetime
from app.services.enrichment.cache import EnrichmentCache
from app.services.enrichment.models import QuickEnrichmentData, DeepEnrichmentData, SourceCallInfo


def test_datetime_serialization_in_quick_data():
    """Test that QuickEnrichmentData with datetime fields can be JSON serialized."""

    # Create sample data with datetime
    quick_data = QuickEnrichmentData(
        company_name="TechStart",
        domain="techstart.com",
        website="https://techstart.com",
        description="Test company",
        industry="Technology",
        quick_completed_at=datetime.now(),  # This is a datetime object
        quick_duration_ms=2000,
        total_cost_usd=0.0,
        sources_called=[
            SourceCallInfo(
                name="metadata",
                success=True,
                cost=0.0,
                duration_ms=500
            )
        ]
    )

    # This should NOT raise "Object of type datetime is not JSON serializable"
    cache = EnrichmentCache()
    serialized = cache._serialize_datetime_fields(quick_data.dict(exclude_none=True))

    # Verify it can be JSON serialized
    json_str = json.dumps(serialized)
    assert json_str is not None

    # Verify datetime was converted to string
    data = json.loads(json_str)
    assert isinstance(data.get("quick_completed_at"), str)
    print("✅ Quick enrichment datetime serialization: PASSED")


def test_datetime_serialization_in_deep_data():
    """Test that DeepEnrichmentData with datetime fields can be JSON serialized."""

    # Create sample data with datetime
    deep_data = DeepEnrichmentData(
        company_name="TechStart",
        domain="techstart.com",
        website="https://techstart.com",
        description="Test company",
        industry="Technology",
        quick_completed_at=datetime.now(),  # datetime
        quick_duration_ms=2000,
        deep_completed_at=datetime.now(),  # datetime
        deep_duration_ms=30000,
        total_cost_usd=0.12,
        sources_called=[
            SourceCallInfo(
                name="clearbit",
                success=True,
                cost=0.10,
                duration_ms=1200
            )
        ]
    )

    # This should NOT raise "Object of type datetime is not JSON serializable"
    cache = EnrichmentCache()
    serialized = cache._serialize_datetime_fields(deep_data.dict(exclude_none=True))

    # Verify it can be JSON serialized
    json_str = json.dumps(serialized)
    assert json_str is not None

    # Verify datetime fields were converted to strings
    data = json.loads(json_str)
    assert isinstance(data.get("quick_completed_at"), str)
    assert isinstance(data.get("deep_completed_at"), str)
    print("✅ Deep enrichment datetime serialization: PASSED")


def test_nested_datetime_serialization():
    """Test that nested datetime objects are properly serialized."""

    cache = EnrichmentCache()

    # Test data with nested datetime
    test_data = {
        "field1": "value1",
        "timestamp": datetime.now(),
        "nested": {
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        "list_of_dicts": [
            {"time": datetime.now()},
            {"time": datetime.now()}
        ]
    }

    # Serialize
    serialized = cache._serialize_datetime_fields(test_data)

    # Verify it can be JSON serialized
    json_str = json.dumps(serialized)
    assert json_str is not None

    # Verify all datetime fields were converted
    data = json.loads(json_str)
    assert isinstance(data["timestamp"], str)
    assert isinstance(data["nested"]["created_at"], str)
    assert isinstance(data["nested"]["updated_at"], str)
    assert isinstance(data["list_of_dicts"][0]["time"], str)
    assert isinstance(data["list_of_dicts"][1]["time"], str)
    print("✅ Nested datetime serialization: PASSED")


if __name__ == "__main__":
    print("Testing datetime JSON serialization fix...")
    print()

    test_datetime_serialization_in_quick_data()
    test_datetime_serialization_in_deep_data()
    test_nested_datetime_serialization()

    print()
    print("=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)
    print()
    print("The cache system now properly serializes datetime objects")
    print("to ISO format strings before storing in Supabase.")
    print()
    print("This fixes the Railway error:")
    print("  'Object of type datetime is not JSON serializable'")
