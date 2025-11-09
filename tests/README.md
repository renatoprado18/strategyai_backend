# Strategy AI Backend - Test Suite

Comprehensive test suite for the Strategy AI Lead Generator backend with unit tests, integration tests, and end-to-end scenarios.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Writing Tests](#writing-tests)
- [Coverage](#coverage)
- [Best Practices](#best-practices)

## Overview

This test suite provides comprehensive coverage of:

- **Core Components**: LLM client, circuit breaker, cache, exceptions
- **Middleware**: Logging, security, CORS
- **Service Layer**: Analysis pipeline, stages, external integrations
- **API Endpoints**: Authentication, submissions, reports, health checks
- **Error Handling**: Rate limiting, validation, circuit breaker behavior

## Test Structure

```
tests/
├── conftest.py                    # Pytest configuration and fixtures
├── README.md                      # This file
│
├── unit/                          # Unit tests for individual components
│   ├── __init__.py
│   ├── test_llm_client.py        # LLM client with retry logic
│   ├── test_circuit_breaker.py   # Circuit breaker states and transitions
│   ├── test_cache.py             # Cache operations
│   ├── test_exceptions.py        # Custom exceptions
│   ├── test_logging_middleware.py # Correlation ID and structured logging
│   ├── test_security_middleware.py # Security headers and request limits
│   │
│   └── services/                  # Service layer tests
│       ├── __init__.py
│       └── test_multistage_pipeline.py # Pipeline orchestration
│
└── integration/                   # Integration tests for API endpoints
    ├── __init__.py
    ├── test_auth_endpoints.py     # Authentication flow
    ├── test_analysis_endpoints.py  # Analysis submission and processing
    └── test_health_endpoints.py   # Health and monitoring
```

## Running Tests

### Install Dependencies

```bash
# Install production and development dependencies
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=html --cov-report=term
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only fast tests (exclude slow tests)
pytest -m "not slow"

# Run smoke tests (critical paths)
pytest -m smoke
```

### Run Specific Test Files

```bash
# Run tests in a specific file
pytest tests/unit/test_llm_client.py

# Run a specific test class
pytest tests/unit/test_llm_client.py::TestLLMClient

# Run a specific test function
pytest tests/unit/test_llm_client.py::TestLLMClient::test_successful_call
```

### Run Tests in Parallel

```bash
# Use all CPU cores
pytest -n auto

# Use specific number of workers
pytest -n 4
```

### Run Tests with Output

```bash
# Show print statements
pytest -s

# Show local variables on failure
pytest -l

# Show full diff on assertion errors
pytest -vv
```

## Test Categories

### Unit Tests (`-m unit`)

Test individual components in isolation with mocked dependencies:

- **test_llm_client.py**: LLM API calls, retry logic, JSON parsing, error handling
- **test_circuit_breaker.py**: State transitions, failure detection, recovery
- **test_cache.py**: Cache key generation, TTL management, retrieval
- **test_exceptions.py**: Custom exception classes and error handling
- **test_logging_middleware.py**: Correlation IDs, structured logging, context
- **test_security_middleware.py**: Security headers, rate limiting, request validation
- **test_multistage_pipeline.py**: Pipeline orchestration, stage execution

### Integration Tests (`-m integration`)

Test API endpoints with realistic scenarios:

- **test_auth_endpoints.py**: Login, signup, JWT validation, protected endpoints
- **test_analysis_endpoints.py**: Submission, processing, status updates, SSE streaming
- **test_health_endpoints.py**: Health checks, circuit breaker monitoring, system status

## Writing Tests

### Basic Test Structure

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
class TestMyComponent:
    """Test suite for MyComponent"""

    @pytest.fixture
    def my_fixture(self):
        """Fixture that provides test data"""
        return {"key": "value"}

    def test_basic_functionality(self, my_fixture):
        """Test basic functionality"""
        result = my_component.process(my_fixture)
        assert result == expected_value

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async functionality"""
        result = await my_async_function()
        assert result is not None
```

### Using Fixtures

Fixtures are defined in `conftest.py` and available to all tests:

```python
def test_with_test_client(test_client):
    """Test using the FastAPI test client"""
    response = test_client.get("/")
    assert response.status_code == 200

async def test_with_async_client(async_client):
    """Test using async client"""
    response = await async_client.get("/")
    assert response.status_code == 200

def test_with_mock_services(mock_openrouter_api, mock_apify_client):
    """Test with mocked external services"""
    # Services are automatically mocked
    result = await call_external_service()
    assert result is not None
```

### Mocking External Services

```python
from unittest.mock import Mock, patch

def test_with_mock(mock_openrouter_api):
    """Test with mocked OpenRouter API"""
    # Mock is already configured in conftest.py
    # You can customize it further if needed
    mock_openrouter_api.json.return_value = {"custom": "data"}
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("test", "TEST"),
    ("hello", "HELLO"),
    ("world", "WORLD"),
])
def test_uppercase(input, expected):
    """Test uppercase conversion with multiple inputs"""
    assert input.upper() == expected
```

## Coverage

### Generate Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

### Coverage Goals

- **Overall**: > 80% code coverage
- **Critical paths**: > 95% coverage
  - Authentication
  - Analysis pipeline
  - Circuit breaker
  - Error handling

### View Coverage in Terminal

```bash
# Show missing lines in terminal
pytest --cov=app --cov-report=term-missing
```

## Best Practices

### 1. Test Organization

- **One test file per module**: Keep tests organized and easy to find
- **Descriptive test names**: Use clear, descriptive names that explain what is being tested
- **Group related tests**: Use test classes to group related tests

### 2. Test Independence

- **No test dependencies**: Each test should be independent and able to run in isolation
- **Clean state**: Use fixtures to ensure clean state for each test
- **No shared mutable state**: Avoid sharing mutable state between tests

### 3. Mocking

- **Mock external services**: Always mock external API calls (OpenRouter, Apify, Perplexity)
- **Mock database**: Mock database operations in unit tests
- **Use fixtures**: Define reusable mocks in conftest.py

### 4. Assertions

- **Clear assertions**: Use descriptive assertion messages
- **Test one thing**: Each test should verify one specific behavior
- **Use appropriate assertions**: Use `assert x in y` instead of `assert y.find(x) >= 0`

### 5. Error Testing

- **Test error cases**: Don't just test happy paths
- **Test edge cases**: Test boundary conditions and edge cases
- **Test error messages**: Verify error messages are helpful

### 6. Async Tests

- **Use pytest-asyncio**: Mark async tests with `@pytest.mark.asyncio`
- **Await all coroutines**: Ensure all async calls are awaited
- **Mock async functions**: Use `AsyncMock` for mocking async functions

### 7. Performance

- **Keep tests fast**: Unit tests should run in milliseconds
- **Mark slow tests**: Use `@pytest.mark.slow` for tests > 1s
- **Run slow tests separately**: `pytest -m "not slow"` for fast feedback

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Scheduled daily runs

### Pre-commit Hooks

Set up pre-commit hooks to run tests before commits:

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure app module is importable
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Async Test Errors**
```bash
# Make sure pytest-asyncio is installed
pip install pytest-asyncio
```

**Fixture Not Found**
```bash
# Check that conftest.py is in the tests/ directory
# Fixtures are automatically discovered from conftest.py
```

**Database Connection Errors**
```bash
# Make sure tests use mocked database
# Check that mock_supabase_client fixture is used
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)

## Contributing

When adding new tests:

1. Follow existing test structure and patterns
2. Add appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`)
3. Document complex test scenarios
4. Ensure tests are fast and independent
5. Update this README if adding new test categories

## Support

For questions or issues:
- Check existing tests for examples
- Review conftest.py for available fixtures
- Consult pytest documentation
- Ask in team Slack channel
