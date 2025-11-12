#!/bin/bash
# Comprehensive test runner for IMENSIAH backend

set -e

echo "======================================"
echo "IMENSIAH Test Suite Runner"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Create reports directory
mkdir -p reports

# 1. Run unit tests
echo ""
print_status "Running Enhanced Enrichment Tests..."
pytest tests/test_enrichment_enhanced.py -v --tb=short || {
    print_error "Enhanced enrichment tests failed"
    exit 1
}

# 2. Run integration tests
echo ""
print_status "Running Integration Tests..."
pytest tests/integration/test_form_enrichment_e2e.py -v --tb=short || {
    print_error "Integration tests failed"
    exit 1
}

# 3. Run error recovery tests
echo ""
print_status "Running Error Recovery Tests..."
pytest tests/test_error_recovery.py -v --tb=short || {
    print_error "Error recovery tests failed"
    exit 1
}

# 4. Run performance tests
echo ""
print_status "Running Performance Tests..."
pytest tests/performance/test_enrichment_speed.py -v --tb=short || {
    print_warning "Performance tests failed (non-critical)"
}

# 5. Generate coverage report
echo ""
print_status "Generating Coverage Report..."
pytest \
    tests/test_enrichment_enhanced.py \
    tests/integration/test_form_enrichment_e2e.py \
    tests/test_error_recovery.py \
    --cov=app/services/enrichment \
    --cov=app/utils \
    --cov-report=html:reports/coverage \
    --cov-report=term-missing \
    --cov-report=xml:reports/coverage.xml \
    || {
    print_warning "Coverage report generation had issues"
}

# 6. Run performance benchmarks (optional)
if [ "$RUN_BENCHMARKS" = "true" ]; then
    echo ""
    print_status "Running Performance Benchmarks..."
    pytest tests/performance/ --benchmark-only --benchmark-autosave || {
        print_warning "Benchmark tests failed (non-critical)"
    }
fi

# 7. Test summary
echo ""
echo "======================================"
print_status "Test Suite Complete!"
echo "======================================"
echo ""
echo "Reports generated in: ./reports/"
echo "  - Coverage HTML: reports/coverage/index.html"
echo "  - Coverage XML:  reports/coverage.xml"
echo ""

# Display coverage summary
if [ -f "reports/coverage.xml" ]; then
    echo "Coverage Summary:"
    echo "----------------"
    python -c "
import xml.etree.ElementTree as ET
tree = ET.parse('reports/coverage.xml')
root = tree.getroot()
coverage = root.attrib
line_rate = float(coverage.get('line-rate', 0)) * 100
print(f'Line Coverage: {line_rate:.2f}%')
" 2>/dev/null || echo "Coverage report available at reports/coverage/index.html"
fi

echo ""
print_status "All critical tests passed!"
