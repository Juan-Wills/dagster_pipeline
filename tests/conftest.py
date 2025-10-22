"""Pytest configuration for dagster_pipeline tests"""

import os
import sys
import io
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock

import pandas as pd
import pytest
from dagster import build_op_context

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
            'output_file_name': 'test_file1_transformed.csv',
            'dataframe': df1,
            'row_count': len(df1),
            'column_count': len(df1.columns),
            'metadata': {
                'parse_info': {'separator': ',', 'encoding': 'utf-8'},
                'rows': len(df1),
                'columns': len(df1.columns),
                'file_id': 'file_id_1'
            }
        },
        {
            'file_name': 'test_file2.csv',
            'output_file_name': 'test_file2_transformed.csv',
            'dataframe': df2,
            'row_count': len(df2),
            'column_count': len(df2.columns),
            'metadata': {
                'parse_info': {'separator': ',', 'encoding': 'utf-8'},
                'rows': len(df2),
                'columns': len(df2.columns),
                'file_id': 'file_id_2'
            }
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
# Mock Resource Fixtures
# ============================================================================

@pytest.fixture
def mock_google_drive():
    """Mock Google Drive resource."""
    mock = MagicMock()
    
    # Mock folder operations
    mock.find_folder_by_name.return_value = 'mock_folder_id_123'
    mock.create_folder_if_not_exists.return_value = 'mock_processed_folder_id'
    
    # Mock file listing
    mock.list_files_in_folder.return_value = [
        {'id': 'file1', 'name': 'test1.csv'},
        {'id': 'file2', 'name': 'test2.csv'}
    ]
    
    # Mock file content download
    # Need at least 3 rows with 3+ unique values per column to pass transformation filters
    sample_csv = "Name,Age,City\nJohn,30,NYC\nJane,25,LA\nBob,35,SF\n"
    mock.get_file_content.return_value = io.BytesIO(sample_csv.encode('utf-8'))
    
    # Mock file upload
    mock.upload_file_from_memory.return_value = {
        'name': 'test_file.csv',
        'id': 'uploaded_file_id',
        'action': 'created'
    }
    
    return mock


@pytest.fixture
def mock_duckdb():
    """Mock DuckDB resource."""
    mock = MagicMock()
    mock.execute_query.return_value = None
    mock.get_connection.return_value = MagicMock()
    return mock


@pytest.fixture
def mock_postgresql():
    """Mock PostgreSQL resource."""
    mock = MagicMock()
    mock.execute_query.return_value = None
    mock.get_connection.return_value = MagicMock()
    mock.test_connection.return_value = True
    return mock


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB resource."""
    mock = MagicMock()
    mock.get_database.return_value = MagicMock()
    mock.test_connection.return_value = True
    
    # Mock collection operations
    mock_collection = MagicMock()
    mock_collection.insert_many.return_value = MagicMock(inserted_ids=['id1', 'id2'])
    mock.get_database.return_value.__getitem__.return_value = mock_collection
    
    return mock


# ============================================================================
# Dagster Context Fixtures
# ============================================================================

@pytest.fixture
def dagster_context():
    """Create a basic Dagster execution context for testing."""
    return build_op_context()


@pytest.fixture
def dagster_context_with_resources(mock_google_drive, mock_duckdb, mock_postgresql, mock_mongodb):
    """Create a Dagster execution context with all mocked resources."""
    return build_op_context(
        resources={
            "google_drive": mock_google_drive,
            "duckdb": mock_duckdb,
            "postgresql": mock_postgresql,
            "mongodb": mock_mongodb,
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
