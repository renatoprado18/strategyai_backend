"""
Server-Sent Events (SSE) Test Client

Utilities for testing SSE streams in FastAPI applications.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SSEEvent:
    """Represents a single SSE event"""
    event_type: str
    data: Dict[str, Any]
    raw_data: str
    timestamp: float


class SSETestClient:
    """
    Test client for Server-Sent Events streams

    Usage:
        client = SSETestClient()
        events = await client.collect_events(stream_url, max_events=3, timeout=10)

        for event in events:
            print(f"Event: {event.event_type}")
            print(f"Data: {event.data}")
    """

    def __init__(self):
        self.events: List[SSEEvent] = []

    async def collect_events(
        self,
        async_client,
        stream_url: str,
        max_events: Optional[int] = None,
        timeout: float = 10.0,
        stop_on_event: Optional[str] = None
    ) -> List[SSEEvent]:
        """
        Collect events from an SSE stream

        Args:
            async_client: httpx AsyncClient instance
            stream_url: SSE stream URL
            max_events: Maximum number of events to collect (None = unlimited)
            timeout: Maximum time to wait in seconds
            stop_on_event: Stop collecting when this event type is received

        Returns:
            List of SSEEvent objects
        """
        events = []
        start_time = asyncio.get_event_loop().time()

        try:
            async with async_client.stream("GET", stream_url) as response:
                if response.status_code != 200:
                    raise Exception(f"SSE stream failed: {response.status_code}")

                current_event_type = None
                current_data = None

                async for line in self._iter_lines(response):
                    # Check timeout
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        logger.warning(f"SSE stream timeout after {timeout}s")
                        break

                    line = line.strip()

                    if not line:
                        # Empty line = event boundary
                        if current_event_type and current_data:
                            event = SSEEvent(
                                event_type=current_event_type,
                                data=current_data,
                                raw_data=json.dumps(current_data),
                                timestamp=asyncio.get_event_loop().time()
                            )
                            events.append(event)
                            logger.debug(f"Captured SSE event: {current_event_type}")

                            # Check stop condition
                            if stop_on_event and current_event_type == stop_on_event:
                                logger.info(f"Stopping on event: {stop_on_event}")
                                break

                            # Check max events
                            if max_events and len(events) >= max_events:
                                logger.info(f"Collected max events: {max_events}")
                                break

                            current_event_type = None
                            current_data = None
                        continue

                    # Parse SSE line
                    if line.startswith("event:"):
                        current_event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()
                        try:
                            current_data = json.loads(data_str)
                        except json.JSONDecodeError:
                            current_data = {"raw": data_str}

        except Exception as e:
            logger.error(f"Error collecting SSE events: {e}", exc_info=True)

        return events

    async def _iter_lines(self, response) -> AsyncIterator[str]:
        """Iterate over response lines"""
        buffer = b""
        async for chunk in response.aiter_bytes():
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                yield line.decode("utf-8")

        # Yield remaining buffer
        if buffer:
            yield buffer.decode("utf-8")

    def find_event(self, events: List[SSEEvent], event_type: str) -> Optional[SSEEvent]:
        """Find first event with given type"""
        for event in events:
            if event.event_type == event_type:
                return event
        return None

    def find_all_events(self, events: List[SSEEvent], event_type: str) -> List[SSEEvent]:
        """Find all events with given type"""
        return [e for e in events if e.event_type == event_type]

    def validate_event_sequence(
        self,
        events: List[SSEEvent],
        expected_sequence: List[str]
    ) -> bool:
        """
        Validate that events occurred in expected sequence

        Args:
            events: List of captured events
            expected_sequence: Expected event types in order

        Returns:
            True if sequence matches
        """
        actual_sequence = [e.event_type for e in events]

        if len(actual_sequence) != len(expected_sequence):
            logger.error(
                f"Event sequence length mismatch: "
                f"expected {len(expected_sequence)}, got {len(actual_sequence)}"
            )
            return False

        for i, (actual, expected) in enumerate(zip(actual_sequence, expected_sequence)):
            if actual != expected:
                logger.error(
                    f"Event sequence mismatch at position {i}: "
                    f"expected '{expected}', got '{actual}'"
                )
                return False

        return True

    def print_event_summary(self, events: List[SSEEvent]):
        """Print summary of captured events"""
        print("\n" + "="*80)
        print("SSE EVENT SUMMARY")
        print("="*80)

        for i, event in enumerate(events, 1):
            print(f"\n[Event {i}] {event.event_type}")
            print("-" * 80)
            print(f"Timestamp: {event.timestamp:.3f}s")
            print(f"Data: {json.dumps(event.data, indent=2)}")

        print("\n" + "="*80)


class MockSSEStream:
    """
    Mock SSE stream for testing without real HTTP requests

    Usage:
        mock = MockSSEStream()
        mock.add_event("layer1_complete", {"fields": {"name": "Google"}})
        mock.add_event("layer2_complete", {"fields": {"employeeCount": "10001+"}})

        events = await mock.collect_events(max_events=2)
    """

    def __init__(self):
        self.events: List[SSEEvent] = []
        self.delay_ms: int = 100  # Delay between events

    def add_event(self, event_type: str, data: Dict[str, Any]):
        """Add an event to the mock stream"""
        self.events.append(SSEEvent(
            event_type=event_type,
            data=data,
            raw_data=json.dumps(data),
            timestamp=0.0
        ))

    async def collect_events(
        self,
        max_events: Optional[int] = None,
        timeout: float = 10.0
    ) -> List[SSEEvent]:
        """Simulate collecting events with delays"""
        collected = []
        start_time = asyncio.get_event_loop().time()

        for event in self.events:
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                break

            # Simulate delay
            await asyncio.sleep(self.delay_ms / 1000.0)

            # Update timestamp
            event.timestamp = asyncio.get_event_loop().time()
            collected.append(event)

            # Check max events
            if max_events and len(collected) >= max_events:
                break

        return collected


# ============================================================================
# PYTEST FIXTURES
# ============================================================================


def pytest_configure(config):
    """Register SSE test fixtures"""
    pass


def sse_test_client():
    """Fixture: SSE test client"""
    return SSETestClient()


def mock_sse_stream():
    """Fixture: Mock SSE stream"""
    return MockSSEStream()
