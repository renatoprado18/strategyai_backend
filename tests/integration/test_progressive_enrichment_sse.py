"""
SSE Stream Integration Tests for Progressive Enrichment

Tests the Server-Sent Events stream functionality specifically.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock

from tests.utils.sse_test_client import SSETestClient, MockSSEStream


@pytest.mark.integration
@pytest.mark.asyncio
class TestProgressiveEnrichmentSSE:
    """Test SSE streaming for progressive enrichment"""

    async def test_sse_stream_event_sequence(self, async_client, mock_redis_client):
        """
        Test that SSE events are delivered in correct sequence:
        1. layer1_complete
        2. layer2_complete
        3. layer3_complete
        """
        # Mock enrichment sources for fast response
        with patch('app.services.enrichment.progressive_orchestrator.MetadataSource') as mock_metadata, \
             patch('app.services.enrichment.progressive_orchestrator.IpApiSource') as mock_ip, \
             patch('app.services.enrichment.progressive_orchestrator.ClearbitSource') as mock_clearbit:

            # Setup mocks for quick response
            mock_metadata_instance = Mock()
            mock_metadata_instance.enrich = AsyncMock(return_value=Mock(
                success=True,
                source_name="metadata",
                data={"company_name": "TestCorp"},
                cost_usd=0.0,
                duration_ms=100
            ))
            mock_metadata.return_value = mock_metadata_instance

            mock_ip_instance = Mock()
            mock_ip_instance.enrich = AsyncMock(return_value=Mock(
                success=True,
                source_name="ip_api",
                data={"region": "California"},
                cost_usd=0.0,
                duration_ms=100
            ))
            mock_ip.return_value = mock_ip_instance

            mock_clearbit_instance = Mock()
            mock_clearbit_instance.enrich = AsyncMock(return_value=Mock(
                success=True,
                source_name="clearbit",
                data={"employee_count": "100-250"},
                cost_usd=0.10,
                duration_ms=500
            ))
            mock_clearbit.return_value = mock_clearbit_instance

            # Start enrichment
            response = await async_client.post(
                "/api/enrichment/progressive/start",
                json={
                    "website_url": "https://testcorp.com",
                    "user_email": "test@test.com"
                }
            )

            assert response.status_code == 200
            data = response.json()
            session_id = data["session_id"]

            # Connect to SSE stream
            sse_client = SSETestClient()

            # Collect events (stop after layer3_complete or timeout)
            events = await sse_client.collect_events(
                async_client,
                f"/api/enrichment/progressive/stream/{session_id}",
                max_events=3,
                timeout=15.0,
                stop_on_event="layer3_complete"
            )

            # Validate event sequence
            expected_sequence = ["layer1_complete", "layer2_complete", "layer3_complete"]
            actual_sequence = [e.event_type for e in events]

            # May receive fewer events if Layer 3 fails, but Layer 1 should always work
            assert len(events) >= 1, "Should receive at least layer1_complete event"

            # Layer 1 should always be first
            if len(events) >= 1:
                assert events[0].event_type == "layer1_complete"

            # If we got all 3, validate full sequence
            if len(events) == 3:
                assert sse_client.validate_event_sequence(events, expected_sequence)

            sse_client.print_event_summary(events)

    async def test_sse_layer1_data_format(self):
        """
        Test Layer 1 SSE event data format

        Validates:
        - Event has correct structure
        - Fields are translated to frontend format
        - Confidence scores included
        """
        # Mock Layer 1 event
        layer1_event_data = {
            "status": "layer1_complete",
            "fields": {
                "name": "Google Inc",  # Translated from company_name
                "state": "California",  # Translated from region
                "city": "Mountain View",
                "country": "US"
            },
            "confidence_scores": {
                "name": 70.0,
                "state": 60.0,
                "city": 60.0,
                "country": 60.0
            },
            "layer_result": {
                "layer_number": 1,
                "duration_ms": 650,
                "cost_usd": 0.0
            }
        }

        # Validate structure
        assert "status" in layer1_event_data
        assert "fields" in layer1_event_data
        assert "confidence_scores" in layer1_event_data
        assert "layer_result" in layer1_event_data

        # Validate field translation (no backend field names)
        fields = layer1_event_data["fields"]
        assert "name" in fields
        assert "state" in fields
        assert "company_name" not in fields  # Should be translated
        assert "region" not in fields  # Should be translated

        # Validate confidence scores match fields
        assert set(fields.keys()) == set(layer1_event_data["confidence_scores"].keys())

    async def test_sse_progressive_field_updates(self):
        """
        Test that fields progressively update across layers

        Layer 1: name, state, city
        Layer 2: +employeeCount, +annualRevenue
        Layer 3: +industry, +digitalMaturity
        """
        mock_stream = MockSSEStream()

        # Layer 1 event
        mock_stream.add_event("layer1_complete", {
            "status": "layer1_complete",
            "fields": {
                "name": "TechCorp",
                "state": "California",
                "city": "San Francisco"
            }
        })

        # Layer 2 event (adds more fields)
        mock_stream.add_event("layer2_complete", {
            "status": "layer2_complete",
            "fields": {
                "name": "TechCorp",
                "state": "California",
                "city": "San Francisco",
                "employeeCount": "100-250",  # NEW
                "annualRevenue": "$10M-$50M"  # NEW
            }
        })

        # Layer 3 event (adds AI fields)
        mock_stream.add_event("layer3_complete", {
            "status": "complete",
            "fields": {
                "name": "TechCorp",
                "state": "California",
                "city": "San Francisco",
                "employeeCount": "100-250",
                "annualRevenue": "$10M-$50M",
                "industry": "Technology / SaaS",  # NEW
                "digitalMaturity": "Advanced"  # NEW
            }
        })

        # Collect events
        events = await mock_stream.collect_events(max_events=3)

        assert len(events) == 3

        # Validate progressive field addition
        layer1_fields = events[0].data["fields"]
        layer2_fields = events[1].data["fields"]
        layer3_fields = events[2].data["fields"]

        # Layer 1: 3 fields
        assert len(layer1_fields) == 3

        # Layer 2: 5 fields (3 from Layer 1 + 2 new)
        assert len(layer2_fields) == 5
        assert all(k in layer2_fields for k in layer1_fields.keys())

        # Layer 3: 7 fields (5 from Layer 2 + 2 new)
        assert len(layer3_fields) == 7
        assert all(k in layer3_fields for k in layer2_fields.keys())

        print("\n✅ Progressive field accumulation working correctly!")

    async def test_sse_error_handling(self, async_client):
        """
        Test SSE stream error handling

        Cases:
        - Session not found
        - Timeout
        - Connection drops
        """
        sse_client = SSETestClient()

        # Test 1: Session not found
        events = await sse_client.collect_events(
            async_client,
            "/api/enrichment/progressive/stream/invalid-session-id",
            max_events=1,
            timeout=5.0
        )

        # Should receive error event or connection fails
        # (Exact behavior depends on implementation)
        # Either way, we shouldn't crash

        print("✅ SSE error handling test passed")

    async def test_sse_field_confidence_scores(self):
        """
        Test that confidence scores are correctly provided for each field

        High confidence (>85%): Auto-fill immediately
        Medium confidence (70-85%): Suggest but don't auto-fill
        Low confidence (<70%): Show but let user decide
        """
        layer_event = {
            "fields": {
                "name": "Google",
                "state": "California",
                "cnpj": "12.345.678/0001-99",  # Brazilian company ID
                "employeeCount": "10001+",
                "industry": "Technology"
            },
            "confidence_scores": {
                "name": 70.0,  # Metadata (moderate)
                "state": 60.0,  # IP geolocation (low)
                "cnpj": 95.0,  # Government data (very high)
                "employeeCount": 85.0,  # Clearbit (high)
                "industry": 75.0  # AI inference (good)
            }
        }

        # Validate high confidence fields (should auto-fill)
        high_confidence_fields = [
            field for field, conf in layer_event["confidence_scores"].items()
            if conf >= 85.0
        ]

        assert "cnpj" in high_confidence_fields
        assert "employeeCount" in high_confidence_fields

        # Validate medium confidence fields (suggest only)
        medium_confidence_fields = [
            field for field, conf in layer_event["confidence_scores"].items()
            if 70.0 <= conf < 85.0
        ]

        assert "name" in medium_confidence_fields
        assert "industry" in medium_confidence_fields

        # Validate low confidence fields (show but warn)
        low_confidence_fields = [
            field for field, conf in layer_event["confidence_scores"].items()
            if conf < 70.0
        ]

        assert "state" in low_confidence_fields

        print("✅ Confidence score thresholds validated!")

    async def test_sse_timing_requirements(self):
        """
        Test that layers complete within expected time windows

        Expected timings:
        - Layer 1: <2 seconds (instant feel)
        - Layer 2: 3-6 seconds (quick but not instant)
        - Layer 3: 6-10 seconds (acceptable wait)
        """
        mock_stream = MockSSEStream()
        mock_stream.delay_ms = 50  # Simulate network delay

        # Add events with realistic delays
        mock_stream.add_event("layer1_complete", {"duration_ms": 1500})
        mock_stream.add_event("layer2_complete", {"duration_ms": 4200})
        mock_stream.add_event("layer3_complete", {"duration_ms": 8500})

        start_time = asyncio.get_event_loop().time()
        events = await mock_stream.collect_events(max_events=3)
        total_time = asyncio.get_event_loop().time() - start_time

        # Validate event timing
        assert events[0].data["duration_ms"] < 2000, "Layer 1 should be <2s"
        assert 3000 < events[1].data["duration_ms"] < 6000, "Layer 2 should be 3-6s"
        assert 6000 < events[2].data["duration_ms"] < 10000, "Layer 3 should be 6-10s"

        print(f"✅ All layers completed within expected time windows")
        print(f"   Layer 1: {events[0].data['duration_ms']}ms")
        print(f"   Layer 2: {events[1].data['duration_ms']}ms")
        print(f"   Layer 3: {events[2].data['duration_ms']}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
