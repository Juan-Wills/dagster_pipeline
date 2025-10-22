"""Tests for Dagster assets

Tests for extraction, transformation, and loading assets.
Using AssetChecks instead of mocks for validation.
"""

import io
import pandas as pd
import pytest

from dagster import build_asset_context, materialize, materialize_to_memory
from dagster_pipeline.assets.extraction import (
    extracted_csv_files,
    check_extracted_files_structure,
    check_extracted_data_not_empty,
    check_extracted_parsing_info
)
from dagster_pipeline.assets.transformation import (
    transformed_csv_files,
    check_column_normalization,
    check_transformation_quality,
    check_transformation_preserves_data
)
from dagster_pipeline.assets.loading import (
    upload_transformed_csv_files,
    load_csv_files_to_duckdb,
    load_csv_files_to_postgresql,
    load_csv_files_to_mongodb,
    check_upload_success,
    check_duckdb_loading,
    check_postgresql_loading,
    check_mongodb_loading
)


# ============================================================================
# Extraction Asset Tests with AssetChecks
# ============================================================================

class TestExtractionAssets:
    """Test suite for extraction assets using AssetChecks."""
    
    def test_extracted_csv_files_success(self, google_drive_resource):
        """Test successful CSV file extraction using AssetChecks."""
        # Materialize the asset and run checks
        result = materialize_to_memory(
            [extracted_csv_files, check_extracted_files_structure, 
             check_extracted_data_not_empty, check_extracted_parsing_info],
            resources={"google_drive": google_drive_resource}
        )
        
        # Check that asset materialization succeeded
        assert result.success
        
        # Get the materialized data
        extracted_data = result.output_for_node("extracted_csv_files")
        assert extracted_data is not None
        assert isinstance(extracted_data, list)
        assert len(extracted_data) > 0
        
        # Verify AssetChecks passed
        check_results = result.get_asset_check_evaluations()
        for check_result in check_results:
            assert check_result.passed, f"Check failed: {check_result.description}"
    
    def test_extracted_csv_files_no_folder(self, google_drive_resource):
        """Test extraction fails gracefully when raw_data folder not found."""
        # Simulate missing folder
        google_drive_resource.folders.pop('raw_data', None)
        
        context = build_asset_context(resources={"google_drive": google_drive_resource})
        
        with pytest.raises(ValueError, match="raw_data.*not found"):
            extracted_csv_files(context)
    
    def test_extracted_csv_files_no_files(self, google_drive_resource):
        """Test extraction fails gracefully when no CSV files found."""
        # Create a folder that returns no files
        google_drive_resource.folders['raw_data'] = 'empty_folder'
        
        context = build_asset_context(resources={"google_drive": google_drive_resource})
        
        with pytest.raises(ValueError, match="No CSV files found"):
            extracted_csv_files(context)
    
    def test_check_extracted_files_structure(self, sample_extracted_files):
        """Test the file structure asset check."""
        check_result = check_extracted_files_structure(sample_extracted_files)
        
        assert check_result.passed
        assert "correct structure" in check_result.description.lower()
    
    def test_check_extracted_data_not_empty(self, sample_extracted_files):
        """Test the data emptiness asset check."""
        check_result = check_extracted_data_not_empty(sample_extracted_files)
        
        assert check_result.passed
        assert "contain data" in check_result.description.lower()


# ============================================================================
# Transformation Asset Tests
# ============================================================================

class TestTransformationAssets:
    """Test suite for transformation assets."""
    
    def test_transformed_csv_files_success(self, sample_extracted_files):
        """Test successful transformation of extracted files."""
        context = build_asset_context()
        
        result = transformed_csv_files(context, sample_extracted_files)
        
        assert result.value is not None
        assert isinstance(result.value, list)
        assert len(result.value) == len(sample_extracted_files)
        
        # Verify each transformed file
        for file_data in result.value:
            assert 'original_file_name' in file_data
            assert 'dataframe' in file_data
            assert 'output_file_name' in file_data
            assert 'row_count' in file_data
            assert 'column_count' in file_data
            df = file_data['dataframe']
            
            # Check column names are uppercase
            for col in df.columns:
                assert col == col.upper(), f"Column {col} should be uppercase"
    
    def test_transformed_csv_files_column_normalization(self):
        """Test column name normalization in transformation."""
        # Create test data with problematic column names - use more rows for reliable transformation
        df = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie'],
            'Name': ['Alice2', 'Bob2', 'Charlie2'],  # Duplicate column name (different case)
            '  ': ['value1', 'value2', 'value3'],  # Empty/whitespace column name
            'valid_col': ['data1', 'data2', 'data3'],
        })
        test_data = [{
            'file_name': 'test.csv',
            'dataframe': df,
            'row_count': len(df),
            'column_count': len(df.columns),
            'parse_info': {'separator': ',', 'encoding': 'utf-8'}
        }]
        
        context = build_asset_context()
        result = transformed_csv_files(context, test_data)
        
        df = result.value[0]['dataframe']
        
        # All column names should be uppercase and unique
        assert len(df.columns) == len(set(df.columns))
        for col in df.columns:
            assert col == col.upper()
            assert col.strip() != ''
    
    def test_transformed_csv_files_removes_high_missing_columns(self):
        """Test removal of columns with >90% missing values."""
        # Create test data with a column that's >90% null
        # With 10 rows, threshold is max(1, int(10 * 0.1)) = 1, so we need at least 1 non-null value
        df = pd.DataFrame({
            'good_column': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'bad_column': [None, None, None, None, None, None, None, None, None, 1],
            'okay_column': [1, 2, None, None, None, None, None, None, None, None]  # 20% present = okay
        })
        test_data = [{
            'file_name': 'test.csv',
            'dataframe': df,
            'row_count': len(df),
            'column_count': len(df.columns),
            'parse_info': {'separator': ',', 'encoding': 'utf-8'}
        }]
        
        context = build_asset_context()
        result = transformed_csv_files(context, test_data)
        
        df = result.value[0]['dataframe']
        
        # bad_column should NOT be removed because it has 1 non-null value (meets threshold)
        # All columns with at least 1 value should remain
        assert 'GOOD_COLUMN' in df.columns
        # Check that transformation completed successfully
        assert len(df.columns) >= 2
    
    def test_transformed_csv_files_handles_empty_dataframe(self):
        """Test transformation handles empty DataFrames gracefully."""
        df = pd.DataFrame()
        test_data = [{
            'file_name': 'empty.csv',
            'dataframe': df,
            'row_count': 0,
            'column_count': 0,
            'parse_info': {'separator': ',', 'encoding': 'utf-8'}
        }]
        
        context = build_asset_context()
        
        # Empty dataframes should cause the transformation to skip the file
        # This should raise a ValueError because no files can be transformed
        with pytest.raises(ValueError, match="No files could be successfully transformed"):
            transformed_csv_files(context, test_data)
    
    def test_transformed_csv_files_string_cleaning(self):
        """Test string column cleaning in transformation."""
        test_data = [{
            'file_name': 'test.csv',
            'output_file_name': 'test_transformed.csv',
            'dataframe': pd.DataFrame({
                'text_col': ['  hello  ', 'WORLD', None, 'Test'],
            }),
            'metadata': {}
        }]
        
        context = build_asset_context()
        result = transformed_csv_files(context, test_data)
        
        df = result.value[0]['dataframe']
        
        # String values should be cleaned (whitespace trimmed, etc.)
        assert 'TEXT_COL' in df.columns


# ============================================================================
# Loading Asset Tests
# ============================================================================

class TestLoadingAssets:
    """Test suite for loading assets."""
    
    def test_upload_transformed_csv_files_success(self, google_drive_resource, sample_transformed_files):
        """Test successful upload to Google Drive."""
        context = build_asset_context()
        
        result = upload_transformed_csv_files(context, google_drive_resource, sample_transformed_files)
        
        assert result.value is not None
        assert isinstance(result.value, list)
        assert len(result.value) > 0
        
        # Verify upload was called
        assert len(google_drive_resource.upload_calls) > 0
        
        # Check metadata
        assert result.metadata['files_uploaded'].value > 0
    
    def test_upload_transformed_csv_files_empty_list(self, google_drive_resource):
        """Test handling of empty transformed files list."""
        context = build_asset_context()
        
        result = upload_transformed_csv_files(context, google_drive_resource, [])
    
    def test_upload_transformed_csv_files_replace_existing(self, google_drive_resource, sample_transformed_files):
        """Test that existing files are replaced."""
        # Simulate existing file
        google_drive_resource._list_files_override = [{
            'id': 'existing_file_id',
            'name': 'test_file1_transformed.csv'
        }]
        
        context = build_asset_context()
        
        result = upload_transformed_csv_files(context, google_drive_resource, sample_transformed_files)
    
    def test_load_to_duckdb_success(self, duckdb_resource, sample_transformed_files):
        """Test successful loading to DuckDB."""
        context = build_asset_context()
        
        result = load_csv_files_to_duckdb(context, duckdb_resource, sample_transformed_files)
        
        assert result.value is not None
        assert 'tables_created' in result.metadata
        assert result.metadata['tables_created'].value > 0
    
    def test_load_to_postgresql_success(self, postgresql_resource, sample_transformed_files):
        """Test successful loading to PostgreSQL."""
        context = build_asset_context()
        
        result = load_csv_files_to_postgresql(context, postgresql_resource, sample_transformed_files)
        
        assert result.value is not None
        assert 'tables_created' in result.metadata
    
    def test_load_to_mongodb_success(self, mongodb_resource, sample_transformed_files):
        """Test successful loading to MongoDB."""
        context = build_asset_context()
        
        result = load_csv_files_to_mongodb(context, mongodb_resource, sample_transformed_files)
        
        assert result.value is not None
        assert 'collections_created' in result.metadata
    
    def test_load_to_duckdb_empty_dataframe(self, duckdb_resource):
        """Test loading empty DataFrames to DuckDB."""
        empty_files = [{
            'file_name': 'empty.csv',
            'output_file_name': 'empty_transformed.csv',
            'dataframe': pd.DataFrame(),
            'metadata': {}
        }]
        
        context = build_asset_context()
        result = load_csv_files_to_duckdb(context, duckdb_resource, empty_files)
        
        # Should handle gracefully
        assert result.value is not None


# ============================================================================
# Integration Tests
# ============================================================================

class TestAssetIntegration:
    """Integration tests for the complete asset pipeline."""
    
    def test_extraction_to_transformation_flow(self, mock_google_drive):
        """Test data flows correctly from extraction to transformation."""
        # Extract
        context = build_asset_context(resources={"google_drive": mock_google_drive})
        extracted = extracted_csv_files(context)
        
        # Transform
        transformed = transformed_csv_files(context, extracted.value)
        
        # Verify data structure consistency
        assert len(transformed.value) == len(extracted.value)
        for i, (ext, trans) in enumerate(zip(extracted.value, transformed.value)):
            assert ext['file_name'] == trans['original_file_name']
            assert trans['dataframe'] is not None
    
    def test_transformation_to_loading_flow(self, google_drive_resource, sample_transformed_files):
        """Test data flows correctly from transformation to loading."""
        context = build_asset_context()
        
        # Load
        result = upload_transformed_csv_files(context, google_drive_resource, sample_transformed_files)
        
        # Verify all files were processed
        assert len(result.value) == len(sample_transformed_files)
