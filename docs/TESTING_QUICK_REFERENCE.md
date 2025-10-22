# Dagster Testing Quick Reference

Quick reference for common testing commands and patterns.

## Quick Start

```bash
# Install dependencies
make install

# Run all tests
make test

# Run tests without coverage (faster)
make test-fast
```

## Common Commands

### Running Tests

```bash
# All tests with coverage
pytest --cov=dagster_pipeline

# All tests verbose
pytest -v

# Specific test file
pytest tests/test_assets.py

# Specific test class
pytest tests/test_assets.py::TestExtractionAssets

# Specific test method
pytest tests/test_assets.py::TestExtractionAssets::test_extracted_csv_files_success

# Run tests matching pattern
pytest -k "extraction"

# Stop on first failure
pytest -x

# Show local variables in tracebacks
pytest -l

# Run last failed tests
pytest --lf

# Run failed tests first
pytest --ff
```

### Coverage

```bash
# Coverage report in terminal
pytest --cov=dagster_pipeline --cov-report=term-missing

# HTML coverage report
pytest --cov=dagster_pipeline --cov-report=html
open htmlcov/index.html

# Check coverage threshold
pytest --cov=dagster_pipeline --cov-fail-under=80
```

### Test Selection

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Database tests only
pytest -m database

# Smoke tests
pytest -m smoke

# Exclude slow tests
pytest -m "not slow"
```

### Debugging

```bash
# Print output (disable capture)
pytest -s

# Drop into debugger on failure
pytest --pdb

# Drop into debugger at start of each test
pytest --trace

# Verbose output with full tracebacks
pytest -vv --tb=long
```

## Make Commands

```bash
make help              # Show all available commands
make install          # Install all dependencies
make test             # Run all tests with coverage
make test-unit        # Run unit tests only
make test-integration # Run integration tests
make test-fast        # Run without coverage (faster)
make test-coverage    # Generate HTML coverage report
make lint             # Run linters
make format           # Format code with black
make clean            # Clean test artifacts
make ci               # Run full CI pipeline locally
```

## Pytest Markers

Use markers to organize and filter tests:

```python
@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.database
@pytest.mark.google_drive
@pytest.mark.smoke
```

## Common Test Patterns

### Basic Asset Test
```python
def test_my_asset(mock_resource):
    context = build_asset_context(resources={"resource": mock_resource})
    result = my_asset(context, mock_resource)
    assert result.value is not None
```

### Test with Fixtures
```python
def test_with_data(sample_csv_data, mock_google_drive):
    context = build_asset_context(resources={"google_drive": mock_google_drive})
    result = process_data(context, sample_csv_data)
    assert len(result) > 0
```

### Test Exceptions
```python
def test_handles_error():
    with pytest.raises(ValueError, match="Invalid input"):
        function_that_raises("bad_input")
```

### Parametrized Tests
```python
@pytest.mark.parametrize("input,expected", [
    ("a", "A"),
    ("b", "B"),
])
def test_multiple_cases(input, expected):
    assert transform(input) == expected
```

### Mock External Service
```python
@patch('module.ExternalService')
def test_with_mock(mock_service):
    mock_service.return_value.method.return_value = "result"
    result = my_function()
    assert result == "result"
```

## Environment Setup

```bash
# Set test environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
export MONGO_HOST=localhost
export MONGO_PORT=27017

# Start database services
docker-compose up -d

# Check service status
docker ps

# Stop services
docker-compose down
```

## Coverage Goals

- **Overall**: 80%+
- **Critical paths**: 100%
- **Resources**: 90%+
- **Assets**: 85%+

## Useful Flags

| Flag | Description |
|------|-------------|
| `-v` | Verbose output |
| `-s` | Show print statements |
| `-x` | Stop on first failure |
| `-k EXPRESSION` | Run tests matching expression |
| `-m MARKER` | Run tests with marker |
| `--lf` | Run last failed |
| `--ff` | Run failed first |
| `--pdb` | Drop into debugger on failure |
| `--cov` | Measure coverage |
| `--tb=short` | Short traceback format |

## Configuration Files

- `pytest.ini` - Pytest configuration
- `conftest.py` - Shared fixtures
- `.coveragerc` - Coverage settings
- `Makefile` - Convenient commands

## Continuous Integration

Tests run automatically on:
- Every push to main/docker/develop branches
- Every pull request
- Can be run locally with `make ci`

## Troubleshooting

```bash
# Can't find module
pip install -e .

# Missing dependencies
pip install --dependency-groups dev,dagster,google-api,databases

# Database connection errors
docker-compose up -d
docker ps

# Clean and retry
make clean
make test
```

## Resources

- [Full Test Documentation](tests/README.md)
- [Testing Best Practices](docs/TESTING_BEST_PRACTICES.md)
- [Dagster Testing Docs](https://docs.dagster.io/concepts/testing)
- [Pytest Documentation](https://docs.pytest.org/)
