# Dagster Pipeline Tests

Comprehensive test suite for the Dagster ETL pipeline following best practices.

## Overview

This test suite provides comprehensive coverage for:
- **Assets**: Extraction, transformation, and loading operations
- **Resources**: Database connections and external services
- **Sensors**: Event-driven automation
- **Integration**: End-to-end pipeline validation
- **Schedules**: Scheduled job execution (future implementation)

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_assets.py           # Asset functionality tests
├── test_resources.py        # Resource connection tests
├── test_sensors.py          # Sensor behavior tests
├── test_integration.py      # End-to-end integration tests
├── test_schedules.py        # Schedule tests (placeholder)
├── test_utils.py            # Test utilities and helpers
└── test_database_connections.py  # Database connectivity tests
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Files
```bash
pytest tests/test_assets.py
pytest tests/test_resources.py
pytest tests/test_sensors.py
```

### Run Specific Test Classes
```bash
pytest tests/test_assets.py::TestExtractionAssets
pytest tests/test_assets.py::TestTransformationAssets
```

### Run Specific Test Methods
```bash
pytest tests/test_assets.py::TestExtractionAssets::test_extracted_csv_files_success
```

### Run Tests with Coverage
```bash
pytest --cov=dagster_pipeline --cov-report=html
```

View the coverage report by opening `htmlcov/index.html` in a browser.

### Run Tests by Marker
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only database tests
pytest -m database

# Run smoke tests
pytest -m smoke
```

### Run Tests with Verbose Output
```bash
pytest -v
pytest -vv  # Extra verbose
```

### Run Tests and Stop on First Failure
```bash
pytest -x
```

## Test Categories

### 1. Unit Tests
Tests individual components in isolation with mocked dependencies.

**Examples:**
- `test_assets.py`: Tests each asset's transformation logic
- `test_resources.py`: Tests resource initialization and methods
- `test_sensors.py`: Tests sensor evaluation logic

**Run unit tests:**
```bash
pytest -m unit
```

### 2. Integration Tests
Tests interactions between components and the complete pipeline flow.

**Examples:**
- `test_integration.py`: Tests complete pipeline execution
- Asset dependency validation
- Resource configuration validation

**Run integration tests:**
```bash
pytest -m integration
```

### 3. Database Tests
Tests that require database connections (PostgreSQL, MongoDB, DuckDB).

**Prerequisites:**
- Docker containers must be running
- Database services must be accessible

**Run database tests:**
```bash
pytest -m database
```

### 4. Smoke Tests
Quick tests to verify basic functionality.

**Run smoke tests:**
```bash
pytest -m smoke
```

## Test Fixtures

### Data Fixtures
Located in `conftest.py`:
- `sample_csv_data`: Sample DataFrame for testing
- `sample_extracted_files`: Mock extracted file structures
- `sample_transformed_files`: Mock transformed file structures

### Resource Fixtures
- `mock_google_drive`: Mocked Google Drive resource
- `mock_duckdb`: Mocked DuckDB resource
- `mock_postgresql`: Mocked PostgreSQL resource
- `mock_mongodb`: Mocked MongoDB resource

### Context Fixtures
- `dagster_context`: Basic Dagster execution context
- `dagster_context_with_resources`: Context with all mocked resources

## Writing New Tests

### Test Naming Conventions
- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Example Test Structure

```python
import pytest
from dagster import build_asset_context

class TestMyAsset:
    """Test suite for my_asset."""
    
    def test_asset_success_case(self, mock_resource):
        """Test asset succeeds with valid input."""
        context = build_asset_context(resources={"resource": mock_resource})
        
        result = my_asset(context, mock_resource)
        
        assert result.value is not None
        assert len(result.value) > 0
    
    def test_asset_error_handling(self, mock_resource):
        """Test asset handles errors gracefully."""
        mock_resource.method.side_effect = Exception("Error")
        context = build_asset_context(resources={"resource": mock_resource})
        
        with pytest.raises(Exception):
            my_asset(context, mock_resource)
```

### Using Fixtures

```python
def test_with_fixtures(sample_csv_data, mock_google_drive):
    """Test using provided fixtures."""
    assert not sample_csv_data.empty
    assert mock_google_drive is not None
```

### Mocking External Services

```python
from unittest.mock import patch, MagicMock

@patch('module.ExternalService')
def test_with_mock(mock_service):
    """Test with mocked external service."""
    mock_service.return_value.method.return_value = "result"
    # Test code here
```

## Best Practices

### 1. Test Independence
- Each test should be independent and not rely on other tests
- Use fixtures for setup and teardown
- Don't share state between tests

### 2. Descriptive Names
- Use clear, descriptive test names that explain what is being tested
- Include the expected outcome in the test name

### 3. Arrange-Act-Assert Pattern
```python
def test_example():
    # Arrange: Set up test data and conditions
    data = create_test_data()
    
    # Act: Execute the code being tested
    result = process_data(data)
    
    # Assert: Verify the results
    assert result.status == "success"
```

### 4. Test Edge Cases
- Test with empty data
- Test with invalid input
- Test with missing values
- Test with extremely large datasets

### 5. Use Appropriate Assertions
```python
# Good
assert result.value is not None
assert len(items) == 5
assert "key" in dictionary

# Avoid
assert result.value  # Ambiguous
```

### 6. Mock External Dependencies
- Always mock external services (Google Drive, databases)
- Use fixtures for consistent mocking
- Verify mock interactions when necessary

## Continuous Integration

### GitHub Actions (Example)
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run tests
        run: pytest --cov=dagster_pipeline
```

## Coverage Goals

- **Overall Coverage**: Target 80%+ code coverage
- **Critical Paths**: 100% coverage for data transformation logic
- **Resources**: 90%+ coverage for resource implementations
- **Assets**: 85%+ coverage for asset logic

Check current coverage:
```bash
pytest --cov=dagster_pipeline --cov-report=term-missing
```

## Troubleshooting

### Tests Failing Due to Missing Dependencies
```bash
# Install all development dependencies
pip install -e ".[dev,dagster,google-api,databases]"
```

### Database Connection Errors
```bash
# Ensure Docker services are running
docker-compose up -d

# Check service status
docker ps

# View service logs
docker-compose logs postgres
docker-compose logs mongodb
```

### Import Errors
```bash
# Ensure project is installed in development mode
pip install -e .

# Verify Python path includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Pytest Not Found
```bash
# Install pytest
pip install pytest pytest-cov

# Or install dev dependencies
pip install -e ".[dev]"
```

## Additional Resources

- [Dagster Testing Documentation](https://docs.dagster.io/concepts/testing)
- [Pytest Documentation](https://docs.pytest.org/)
- [Python Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

## Contributing

When contributing new features:
1. Write tests before implementing the feature (TDD)
2. Ensure all tests pass before submitting PR
3. Maintain or improve code coverage
4. Update test documentation as needed

## Contact

For questions or issues with tests, please open an issue in the repository.
