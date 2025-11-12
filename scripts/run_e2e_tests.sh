#!/bin/bash

# End-to-End Test Runner for Progressive Enrichment
# Runs comprehensive E2E tests and generates detailed reports

set -e  # Exit on error

echo "========================================="
echo "Progressive Enrichment E2E Test Suite"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
TEST_PATTERN="test_progressive_enrichment_*"
TEST_DIR="tests/integration"
REPORT_DIR="docs/test_reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create report directory
mkdir -p "$REPORT_DIR"

echo "Configuration:"
echo "  Test Pattern: $TEST_PATTERN"
echo "  Test Directory: $TEST_DIR"
echo "  Report Directory: $REPORT_DIR"
echo ""

# Run unit tests for field translation first
echo -e "${YELLOW}[1/4] Running field translation unit tests...${NC}"
pytest tests/unit/test_field_translation.py -v --tb=short || {
    echo -e "${RED}❌ Field translation tests failed!${NC}"
    exit 1
}
echo -e "${GREEN}✅ Field translation tests passed${NC}"
echo ""

# Run E2E integration tests
echo -e "${YELLOW}[2/4] Running E2E integration tests...${NC}"
pytest "$TEST_DIR/$TEST_PATTERN" -v --tb=short --log-cli-level=INFO || {
    echo -e "${RED}❌ E2E integration tests failed!${NC}"
    exit 1
}
echo -e "${GREEN}✅ E2E integration tests passed${NC}"
echo ""

# Run SSE stream tests
echo -e "${YELLOW}[3/4] Running SSE stream tests...${NC}"
pytest tests/integration/test_progressive_enrichment_sse.py -v --tb=short || {
    echo -e "${RED}❌ SSE stream tests failed!${NC}"
    exit 1
}
echo -e "${GREEN}✅ SSE stream tests passed${NC}"
echo ""

# Generate coverage report
echo -e "${YELLOW}[4/4] Generating test coverage report...${NC}"
pytest "$TEST_DIR/$TEST_PATTERN" \
    tests/unit/test_field_translation.py \
    tests/integration/test_progressive_enrichment_sse.py \
    --cov=app.routes.enrichment_progressive \
    --cov=app.services.enrichment.progressive_orchestrator \
    --cov-report=html:"$REPORT_DIR/coverage_$TIMESTAMP" \
    --cov-report=term \
    --quiet || {
    echo -e "${RED}❌ Coverage report generation failed!${NC}"
    exit 1
}
echo -e "${GREEN}✅ Coverage report generated${NC}"
echo ""

# Print summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "Reports generated:"
echo "  - Coverage: $REPORT_DIR/coverage_$TIMESTAMP/index.html"
echo "  - E2E Report: docs/E2E_TEST_REPORT.md"
echo ""

# Optional: Open coverage report in browser (comment out if not needed)
# open "$REPORT_DIR/coverage_$TIMESTAMP/index.html" 2>/dev/null || \
# xdg-open "$REPORT_DIR/coverage_$TIMESTAMP/index.html" 2>/dev/null || \
# echo "Open $REPORT_DIR/coverage_$TIMESTAMP/index.html in your browser to view coverage"

echo "========================================="
echo -e "${GREEN}E2E Test Suite Complete!${NC}"
echo "========================================="

exit 0
