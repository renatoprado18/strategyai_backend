#!/bin/bash
# ============================================================================
# TEST RUNNER SCRIPT
# ============================================================================
# Convenience script for running tests with common configurations
# Usage: ./run_tests.sh [options]
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    print_error "pytest not found. Please install dependencies:"
    echo "  pip install -r requirements-dev.txt"
    exit 1
fi

# Default options
RUN_COVERAGE=false
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_PARALLEL=false
VERBOSE=false
MARKERS=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            RUN_COVERAGE=true
            shift
            ;;
        --unit|-u)
            RUN_UNIT=true
            shift
            ;;
        --integration|-i)
            RUN_INTEGRATION=true
            shift
            ;;
        --parallel|-p)
            RUN_PARALLEL=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./run_tests.sh [options]"
            echo ""
            echo "Options:"
            echo "  -c, --coverage      Run tests with coverage report"
            echo "  -u, --unit          Run only unit tests"
            echo "  -i, --integration   Run only integration tests"
            echo "  -p, --parallel      Run tests in parallel"
            echo "  -v, --verbose       Verbose output"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run_tests.sh                    # Run all tests"
            echo "  ./run_tests.sh --unit             # Run only unit tests"
            echo "  ./run_tests.sh --coverage         # Run with coverage"
            echo "  ./run_tests.sh -u -c              # Unit tests with coverage"
            echo "  ./run_tests.sh -i -p              # Integration tests in parallel"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

# Add markers
if [ "$RUN_UNIT" = true ]; then
    MARKERS="-m unit"
    print_header "Running Unit Tests"
elif [ "$RUN_INTEGRATION" = true ]; then
    MARKERS="-m integration"
    print_header "Running Integration Tests"
else
    print_header "Running All Tests"
fi

# Add coverage
if [ "$RUN_COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=html --cov-report=term-missing"
    print_warning "Coverage report will be generated in htmlcov/"
fi

# Add parallel
if [ "$RUN_PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
    print_warning "Running tests in parallel"
fi

# Add verbose
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
fi

# Add markers
PYTEST_CMD="$PYTEST_CMD $MARKERS"

# Print command
echo ""
echo "Command: $PYTEST_CMD"
echo ""

# Run tests
$PYTEST_CMD

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    print_success "All tests passed!"

    if [ "$RUN_COVERAGE" = true ]; then
        echo ""
        print_success "Coverage report generated: htmlcov/index.html"
    fi

    exit 0
else
    echo ""
    print_error "Some tests failed"
    exit 1
fi
