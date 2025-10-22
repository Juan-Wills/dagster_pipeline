"""Pytest configuration for dagster_pipeline tests"""

import os
import sys
import io
from pathlib import Path
from typing import Dict, List

import pandas as pd
import pytest
from dagster import build_op_context, build_asset_context

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_csv_data() -> pd.DataFrame:
    """Sample CSV data for testing."""
    return pd.DataFrame({
        'Name': ['John Doe', 'Jane Smith', None, 'Bob Wilson'],
        'Age': [30, 25, 35, None],
        'City': ['New York', 'Los Angeles', 'Chicago', 'Houston'],
        'Salary': [50000.0, 60000.0, None, 70000.0],
        '   ': [None, None, None, None],  # Column with excessive missing values
    })


@pytest.fixture
def sample_csv_with_special_encoding() -> bytes:
    """Sample CSV content with special encoding (ISO-8859-1)."""
    data = "Name»Age»City\nJosé»30»São Paulo\nMaria»25»México\n"
    return data.encode('ISO-8859-1')


@pytest.fixture
def sample_extracted_files() -> List[Dict]:
    """Sample extracted files data structure."""
    df1 = pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie'],
        'value': [100, 200, 300]
    })
    df2 = pd.DataFrame({
        'product': ['Widget', 'Gadget', 'Tool'],
        'price': [10.5, 20.0, 15.75]
    })
    
    return [
        {
            'file_name': 'test_file1.csv',
            'dataframe': df1,
            'row_count': len(df1),
            'column_count': len(df1.columns),
            'parse_info': {'separator': ',', 'encoding': 'utf-8'}
        },
        {
            'file_name': 'test_file2.csv',
            'dataframe': df2,
            'row_count': len(df2),
            'column_count': len(df2.columns),
            'parse_info': {'separator': ',', 'encoding': 'utf-8'}
        }
    ]


@pytest.fixture
def sample_transformed_files() -> List[Dict]:
    """Sample transformed files data structure - matches transformation asset output format."""
    df = pd.DataFrame({
        'NAME': ['Alice', 'Bob'],
        'VALUE': [100, 200]
    })
    
    return [
        {
            'original_file_name': 'test_file1.csv',
            'output_file_name': 'test_file1_transformed.csv',
            'dataframe': df,
            'row_count': len(df),
            'column_count': len(df.columns)
        }
    ]


# ============================================================================
# Test Resource Fixtures (using fake implementations instead of mocks)
# ============================================================================

from tests.fake_resources import (
    FakeGoogleDriveResource,
    FakeDuckDBResource,
    FakePostgreSQLResource,
    FakeMongoDBResource
)


@pytest.fixture
def google_drive_resource():
    """Fake Google Drive resource for testing."""
    return FakeGoogleDriveResource()


@pytest.fixture
def duckdb_resource():
    """Fake DuckDB resource for testing."""
    return FakeDuckDBResource()


@pytest.fixture
def postgresql_resource():
    """Fake PostgreSQL resource for testing."""
    return FakePostgreSQLResource()


@pytest.fixture
def mongodb_resource():
    """Fake MongoDB resource for testing."""
    return FakeMongoDBResource()


# Legacy aliases for backwards compatibility
@pytest.fixture
def mock_google_drive(google_drive_resource):
    """Legacy alias for google_drive_resource."""
    return google_drive_resource


@pytest.fixture
def mock_duckdb(duckdb_resource):
    """Legacy alias for duckdb_resource."""
    return duckdb_resource


@pytest.fixture
def mock_postgresql(postgresql_resource):
    """Legacy alias for postgresql_resource."""
    return postgresql_resource


@pytest.fixture
def mock_mongodb(mongodb_resource):
    """Legacy alias for mongodb_resource."""
    return mongodb_resource


# ============================================================================
# Dagster Context Fixtures
# ============================================================================

@pytest.fixture
def dagster_context():
    """Create a basic Dagster execution context for testing."""
    return build_op_context()


@pytest.fixture
def dagster_context_with_resources(google_drive_resource, duckdb_resource, 
                                   postgresql_resource, mongodb_resource):
    """Create a Dagster execution context with all test resources."""
    return build_asset_context(
        resources={
            "google_drive": google_drive_resource,
            "duckdb": duckdb_resource,
            "postgresql": postgresql_resource,
            "mongodb": mongodb_resource,
        }
    )


# ============================================================================
# Environment Setup
# ============================================================================

@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    # Store original values
    original_env = {}
    test_env_vars = {
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5433',
        'POSTGRES_DB': 'test_db',
        'POSTGRES_USER': 'test_user',
        'POSTGRES_PASSWORD': 'test_password',
        'MONGO_HOST': 'localhost',
        'MONGO_PORT': '27017',
        'MONGO_DB': 'test_db',
        'MONGO_ROOT_USER': 'test_user',
        'MONGO_ROOT_PASSWORD': 'test_password',
        'MONGO_AUTH_SOURCE': 'admin',
    }
    
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original values
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
