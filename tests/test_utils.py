"""Test utilities and helper functions

Common utilities used across multiple test files.
"""

import io
import pandas as pd
from typing import Dict, List, Any
from unittest.mock import MagicMock


# ============================================================================
# Data Generation Helpers
# ============================================================================

def create_sample_dataframe(rows: int = 10, cols: int = 3) -> pd.DataFrame:
    """
    Create a sample DataFrame for testing.
    
    Args:
        rows: Number of rows
        cols: Number of columns
        
    Returns:
        Sample DataFrame
    """
    data = {}
    for i in range(cols):
        data[f'col_{i}'] = list(range(rows))
    return pd.DataFrame(data)


def create_csv_bytes(data: pd.DataFrame, encoding: str = 'utf-8', sep: str = ',') -> bytes:
    """
    Convert a DataFrame to CSV bytes.
    
    Args:
        data: DataFrame to convert
        encoding: Text encoding
        sep: Column separator
        
    Returns:
        CSV data as bytes
    """
    csv_string = data.to_csv(index=False, sep=sep)
    return csv_string.encode(encoding)


def create_csv_file_object(data: pd.DataFrame, encoding: str = 'utf-8', sep: str = ',') -> io.BytesIO:
    """
    Create a file-like object containing CSV data.
    
    Args:
        data: DataFrame to convert
        encoding: Text encoding
        sep: Column separator
        
    Returns:
        BytesIO object with CSV data
    """
    csv_bytes = create_csv_bytes(data, encoding, sep)
    return io.BytesIO(csv_bytes)


def create_extracted_file_structure(
    file_name: str,
    dataframe: pd.DataFrame,
    separator: str = ',',
    encoding: str = 'utf-8'
) -> Dict[str, Any]:
    """
    Create a file structure matching the extracted_csv_files asset output.
    
    Args:
        file_name: Name of the file
        dataframe: Data content
        separator: CSV separator used
        encoding: Encoding used
        
    Returns:
        Dictionary with file metadata and data
    """
    return {
        'file_name': file_name,
        'output_file_name': file_name.replace('.csv', '_transformed.csv'),
        'dataframe': dataframe,
        'metadata': {
            'parse_info': {'separator': separator, 'encoding': encoding},
            'rows': len(dataframe),
            'columns': len(dataframe.columns),
        }
    }


# ============================================================================
# Mock Resource Helpers
# ============================================================================

def create_mock_google_drive_service() -> MagicMock:
    """
    Create a mock Google Drive service object.
    
    Returns:
        Mocked Google Drive service
    """
    mock_service = MagicMock()
    
    # Mock files().list() chain
    mock_list = MagicMock()
    mock_list.execute.return_value = {'files': []}
    mock_service.files().list.return_value = mock_list
    
    # Mock files().get_media() chain
    mock_media = MagicMock()
    mock_service.files().get_media.return_value = mock_media
    
    # Mock files().create() chain
    mock_create = MagicMock()
    mock_create.execute.return_value = {'id': 'new_file_id'}
    mock_service.files().create.return_value = mock_create
    
    return mock_service


def create_mock_database_connection() -> MagicMock:
    """
    Create a mock database connection object.
    
    Returns:
        Mocked database connection
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock cursor methods
    mock_cursor.execute.return_value = None
    mock_cursor.fetchone.return_value = ('test_value',)
    mock_cursor.fetchall.return_value = [('test_value',)]
    
    return mock_conn


# ============================================================================
# Assertion Helpers
# ============================================================================

def assert_dataframe_equal(df1: pd.DataFrame, df2: pd.DataFrame, check_dtype: bool = False):
    """
    Assert that two DataFrames are equal.
    
    Args:
        df1: First DataFrame
        df2: Second DataFrame
        check_dtype: Whether to check data types
    """
    pd.testing.assert_frame_equal(df1, df2, check_dtype=check_dtype)


def assert_has_required_keys(data: Dict, required_keys: List[str]):
    """
    Assert that a dictionary has all required keys.
    
    Args:
        data: Dictionary to check
        required_keys: List of required keys
    """
    missing_keys = [key for key in required_keys if key not in data]
    assert not missing_keys, f"Missing required keys: {missing_keys}"


def assert_columns_uppercase(df: pd.DataFrame):
    """
    Assert that all DataFrame column names are uppercase.
    
    Args:
        df: DataFrame to check
    """
    for col in df.columns:
        assert col == col.upper(), f"Column {col} is not uppercase"


def assert_no_high_missing_columns(df: pd.DataFrame, threshold: float = 0.9):
    """
    Assert that no columns have excessive missing values.
    
    Args:
        df: DataFrame to check
        threshold: Maximum allowed missing ratio (0-1)
    """
    missing_ratios = df.isnull().sum() / len(df)
    high_missing = missing_ratios[missing_ratios > threshold]
    assert len(high_missing) == 0, f"Columns with >{threshold*100}% missing: {high_missing.to_dict()}"


# ============================================================================
# File System Helpers
# ============================================================================

def create_temp_csv_file(tmp_path, file_name: str, data: pd.DataFrame) -> str:
    """
    Create a temporary CSV file for testing.
    
    Args:
        tmp_path: pytest tmp_path fixture
        file_name: Name of the file
        data: DataFrame to write
        
    Returns:
        Path to the created file
    """
    file_path = tmp_path / file_name
    data.to_csv(file_path, index=False)
    return str(file_path)


# ============================================================================
# Validation Helpers
# ============================================================================

def validate_extracted_file_structure(file_data: Dict) -> bool:
    """
    Validate that a file data structure matches expected format.
    
    Args:
        file_data: File data dictionary
        
    Returns:
        True if valid
    """
    required_keys = ['file_name', 'dataframe', 'output_file_name', 'metadata']
    assert_has_required_keys(file_data, required_keys)
    
    assert isinstance(file_data['dataframe'], pd.DataFrame)
    assert isinstance(file_data['metadata'], dict)
    
    return True


def validate_transformed_file_structure(file_data: Dict) -> bool:
    """
    Validate that a transformed file data structure matches expected format.
    
    Args:
        file_data: File data dictionary
        
    Returns:
        True if valid
    """
    required_keys = ['file_name', 'dataframe', 'output_file_name', 'metadata']
    assert_has_required_keys(file_data, required_keys)
    
    assert isinstance(file_data['dataframe'], pd.DataFrame)
    assert_columns_uppercase(file_data['dataframe'])
    
    return True


# ============================================================================
# Performance Testing Helpers
# ============================================================================

def create_large_dataframe(rows: int = 100000, cols: int = 10) -> pd.DataFrame:
    """
    Create a large DataFrame for performance testing.
    
    Args:
        rows: Number of rows
        cols: Number of columns
        
    Returns:
        Large DataFrame
    """
    import numpy as np
    
    data = {}
    for i in range(cols):
        if i % 2 == 0:
            data[f'numeric_col_{i}'] = np.random.rand(rows)
        else:
            data[f'string_col_{i}'] = [f'value_{j}' for j in range(rows)]
    
    return pd.DataFrame(data)


# ============================================================================
# Environment Helpers
# ============================================================================

def set_test_environment_variables():
    """Set up test environment variables."""
    import os
    
    test_env = {
        'DAGSTER_HOME': '/tmp/dagster_test',
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5433',
        'MONGO_HOST': 'localhost',
        'MONGO_PORT': '27017',
    }
    
    for key, value in test_env.items():
        os.environ.setdefault(key, value)


def cleanup_test_environment():
    """Clean up test artifacts."""
    import os
    import shutil
    
    # Clean up temporary directories
    test_dirs = ['/tmp/dagster_test']
    for dir_path in test_dirs:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
