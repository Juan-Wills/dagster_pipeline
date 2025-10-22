# Dagster Testing Best Practices Guide

This document outlines the testing strategy and best practices for the Dagster pipeline project.

## Table of Contents
1. [Testing Philosophy](#testing-philosophy)
2. [Test Structure](#test-structure)
3. [Testing Dagster Assets](#testing-dagster-assets)
4. [Testing Resources](#testing-resources)
5. [Testing Sensors](#testing-sensors)
6. [Mocking Strategies](#mocking-strategies)
7. [Integration Testing](#integration-testing)
8. [Performance Testing](#performance-testing)
9. [CI/CD Integration](#cicd-integration)
10. [Common Patterns](#common-patterns)

## Testing Philosophy

### Goals
- **Confidence**: Tests should give us confidence that our pipeline works correctly
- **Speed**: Tests should run quickly to enable rapid development
- **Clarity**: Tests should be easy to understand and maintain
- **Coverage**: Aim for 80%+ code coverage on critical paths

### Test Pyramid
```
        /\
       /  \      E2E Tests (Few)
      /    \
     /------\    Integration Tests (Some)
    /        \
   /----------\  Unit Tests (Many)
  /____________\
```

## Test Structure

### Directory Organization
```
tests/
├── conftest.py              # Shared fixtures
├── test_assets.py           # Asset tests
├── test_resources.py        # Resource tests
├── test_sensors.py          # Sensor tests
├── test_integration.py      # Integration tests
├── test_schedules.py        # Schedule tests
├── test_utils.py            # Test utilities
└── README.md                # Test documentation
```

### Naming Conventions
- **Files**: `test_*.py`
- **Classes**: `Test*` (e.g., `TestExtractionAssets`)
- **Methods**: `test_*_*` (e.g., `test_extracted_csv_files_success`)

### Test Method Naming Pattern
```
test_<what>_<condition>_<expected_outcome>

Examples:
- test_extraction_with_valid_data_succeeds
- test_transformation_with_empty_dataframe_handles_gracefully
- test_loading_with_connection_error_raises_exception
```

## Testing Dagster Assets

### Basic Asset Test Structure
```python
from dagster import build_asset_context

def test_my_asset(mock_resource):
    # Arrange
    context = build_asset_context(resources={"resource": mock_resource})
    input_data = create_test_data()
    
    # Act
    result = my_asset(context, mock_resource, input_data)
    
    # Assert
    assert result.value is not None
    assert result.metadata['row_count'] == 10
```

### Testing Asset Dependencies
```python
def test_asset_dependency_chain():
    # Test that data flows correctly between assets
    context = build_asset_context()
    
    # Step 1: Extract
    extracted = extract_asset(context)
    
    # Step 2: Transform (depends on extract)
    transformed = transform_asset(context, extracted.value)
    
    # Step 3: Load (depends on transform)
    loaded = load_asset(context, transformed.value)
    
    assert loaded.value is not None
```

### Testing Asset Metadata
```python
def test_asset_emits_metadata():
    context = build_asset_context()
    result = my_asset(context)
    
    # Check metadata is present
    assert 'row_count' in result.metadata
    assert 'processing_time' in result.metadata
    assert result.metadata['row_count'] > 0
```

### Testing Asset Error Handling
```python
def test_asset_handles_error(mock_resource):
    mock_resource.method.side_effect = Exception("Connection failed")
    context = build_asset_context(resources={"resource": mock_resource})
    
    with pytest.raises(Exception, match="Connection failed"):
        my_asset(context, mock_resource)
```

## Testing Resources

### Resource Initialization Tests
```python
def test_resource_initialization():
    resource = MyResource(
        host="localhost",
        port=5432,
        database="test_db"
    )
    
    assert resource.host == "localhost"
    assert resource.port == 5432
```

### Resource Connection Tests
```python
@patch('module.connection_library')
def test_resource_connection(mock_library):
    mock_conn = MagicMock()
    mock_library.connect.return_value = mock_conn
    
    resource = MyResource(host="localhost")
    conn = resource.get_connection()
    
    assert conn is not None
    mock_library.connect.assert_called_once()
```

### Resource Error Handling
```python
@patch('module.connection_library')
def test_resource_connection_failure(mock_library):
    mock_library.connect.side_effect = ConnectionError("Failed")
    
    resource = MyResource(host="localhost")
    
    with pytest.raises(ConnectionError):
        resource.get_connection()
```

### Resource Cleanup Tests
```python
@patch('module.connection_library')
def test_resource_cleanup(mock_library):
    mock_conn = MagicMock()
    mock_library.connect.return_value = mock_conn
    
    resource = MyResource(host="localhost")
    conn = resource.get_connection()
    resource.teardown()
    
    mock_conn.close.assert_called_once()
```

## Testing Sensors

### Basic Sensor Test
```python
from dagster import build_sensor_context, RunRequest, SkipReason

def test_sensor_triggers_on_new_file(mock_external_service):
    mock_external_service.list_files.return_value = [
        {'id': 'file1', 'name': 'new.csv'}
    ]
    
    context = build_sensor_context(cursor=None)
    result = my_sensor(context, mock_external_service)
    
    assert isinstance(result, RunRequest)
```

### Testing Sensor Cursor Management
```python
import json

def test_sensor_updates_cursor(mock_external_service):
    mock_external_service.list_files.return_value = [
        {'id': 'file1', 'name': 'file1.csv'}
    ]
    
    context = build_sensor_context(cursor=None)
    result = my_sensor(context, mock_external_service)
    
    # Verify cursor is updated in RunRequest
    if isinstance(result, RunRequest):
        # Check that cursor logic works
        assert True
```

### Testing Sensor Skip Conditions
```python
def test_sensor_skips_when_no_changes(mock_external_service):
    mock_external_service.list_files.return_value = []
    
    context = build_sensor_context()
    result = my_sensor(context, mock_external_service)
    
    assert isinstance(result, SkipReason)
    assert "No files" in str(result)
```

## Mocking Strategies

### External API Mocking
```python
@patch('module.external_api.Client')
def test_with_external_api(mock_client):
    mock_instance = MagicMock()
    mock_client.return_value = mock_instance
    mock_instance.fetch_data.return_value = {'data': 'test'}
    
    result = function_using_api()
    
    assert result == {'data': 'test'}
    mock_instance.fetch_data.assert_called_once()
```

### Database Mocking
```python
@patch('psycopg2.connect')
def test_with_database(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    # Test database operations
    resource = PostgreSQLResource(host="localhost")
    resource.execute_query("SELECT 1")
    
    mock_cursor.execute.assert_called_with("SELECT 1")
```

### File System Mocking
```python
def test_with_temp_files(tmp_path):
    # pytest provides tmp_path fixture
    test_file = tmp_path / "test.csv"
    test_file.write_text("col1,col2\n1,2\n")
    
    result = process_file(str(test_file))
    
    assert result is not None
```

## Integration Testing

### Testing Complete Pipeline Flow
```python
def test_complete_pipeline_flow(
    mock_google_drive,
    mock_duckdb,
    mock_postgresql,
    mock_mongodb
):
    # Test the complete flow from extraction to loading
    context = build_asset_context(resources={
        "google_drive": mock_google_drive,
        "duckdb": mock_duckdb,
        "postgresql": mock_postgresql,
        "mongodb": mock_mongodb,
    })
    
    # Extract
    extracted = extract_asset(context, mock_google_drive)
    assert extracted.value is not None
    
    # Transform
    transformed = transform_asset(context, extracted.value)
    assert transformed.value is not None
    
    # Load
    loaded = load_asset(context, mock_mongodb, transformed.value)
    assert loaded.value is not None
```

### Testing Asset Graph
```python
def test_asset_graph_validation():
    from dagster_pipeline.definitions import defs
    
    # Verify all assets load without errors
    assets = list(defs.assets)
    assert len(assets) > 0
    
    # Verify no circular dependencies
    # (Dagster will raise error if there are cycles)
```

## Performance Testing

### Testing with Large Datasets
```python
import time

def test_performance_with_large_dataset():
    # Create large dataset
    large_df = pd.DataFrame({
        'col1': range(1000000),
        'col2': range(1000000)
    })
    
    start_time = time.time()
    result = process_dataframe(large_df)
    elapsed_time = time.time() - start_time
    
    # Assert performance threshold
    assert elapsed_time < 5.0  # Should complete in under 5 seconds
    assert len(result) == 1000000
```

### Memory Usage Testing
```python
import tracemalloc

def test_memory_efficiency():
    tracemalloc.start()
    
    # Run memory-intensive operation
    result = process_large_file()
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Assert memory usage is reasonable
    assert peak < 100 * 1024 * 1024  # Less than 100MB
```

## CI/CD Integration

### GitHub Actions Workflow
See `.github/workflows/tests.yml` for the complete workflow.

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks:
      - id: black
  
  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

## Common Patterns

### Testing Data Transformations
```python
def test_data_transformation():
    # Input data
    input_df = pd.DataFrame({
        'Name': ['john', 'JANE', 'Bob'],
        'Value': [1, 2, 3]
    })
    
    # Transform
    result_df = transform_function(input_df)
    
    # Assertions
    assert all(result_df['NAME'] == result_df['NAME'].str.upper())
    assert 'VALUE' in result_df.columns
```

### Testing Error Recovery
```python
def test_partial_failure_recovery():
    files = [
        {'name': 'good1.csv', 'data': valid_data},
        {'name': 'bad.csv', 'data': invalid_data},
        {'name': 'good2.csv', 'data': valid_data},
    ]
    
    results = process_files_with_error_handling(files)
    
    # Should process 2 good files despite 1 failure
    assert len(results['success']) == 2
    assert len(results['failed']) == 1
```

### Testing Idempotency
```python
def test_operation_is_idempotent():
    data = create_test_data()
    
    # Run twice
    result1 = idempotent_operation(data)
    result2 = idempotent_operation(data)
    
    # Results should be identical
    pd.testing.assert_frame_equal(result1, result2)
```

## Tips and Tricks

### 1. Use Fixtures for Complex Setup
```python
@pytest.fixture
def complex_test_environment():
    # Setup
    env = setup_complex_environment()
    yield env
    # Teardown
    cleanup_environment(env)
```

### 2. Parametrize Tests for Multiple Cases
```python
@pytest.mark.parametrize("input,expected", [
    ("test.csv", "test_transformed.csv"),
    ("data.csv", "data_transformed.csv"),
    ("file.CSV", "file_transformed.csv"),
])
def test_filename_transformation(input, expected):
    result = transform_filename(input)
    assert result == expected
```

### 3. Use Markers for Test Organization
```python
@pytest.mark.unit
@pytest.mark.fast
def test_simple_function():
    assert simple_function() == expected

@pytest.mark.integration
@pytest.mark.slow
def test_complete_pipeline():
    # Long-running integration test
    pass
```

### 4. Capture Logs in Tests
```python
def test_with_logging(caplog):
    with caplog.at_level(logging.INFO):
        function_that_logs()
    
    assert "Expected log message" in caplog.text
```

### 5. Test Async Code
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected
```

## Conclusion

Following these best practices will help maintain a robust, reliable test suite that:
- Catches bugs early
- Enables confident refactoring
- Documents expected behavior
- Supports rapid development

Remember: **Good tests are an investment in code quality and developer productivity.**
