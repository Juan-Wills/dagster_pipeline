"""Simple demonstration of AssetCheck-based testing

This file demonstrates the new testing approach using AssetChecks
instead of mocks for validation.
"""

import pandas as pd
import pytest
from dagster import materialize_to_memory, build_asset_context

from dagster_pipeline.assets.extraction import (
    extracted_csv_files,
    check_extracted_files_structure,
    check_extracted_data_not_empty
)
from dagster_pipeline.assets.transformation import (
    transformed_csv_files,
    check_column_normalization,
    check_transformation_quality
)
from tests.fake_resources import FakeGoogleDriveResource


class TestAssetCheckApproach:
    """Demonstrates using AssetChecks instead of mocks."""
    
    def test_extraction_with_asset_checks(self):
        """Test extraction asset with integrated asset checks."""
        # Create fake resource (no mocks!)
        google_drive = FakeGoogleDriveResource()
        
        # Materialize asset WITH its checks
        result = materialize_to_memory(
            [extracted_csv_files, check_extracted_files_structure, 
             check_extracted_data_not_empty],
            resources={"google_drive": google_drive}
        )
        
        # Verify materialization succeeded
        assert result.success
        
        # Get the materialized output
        extracted_data = result.output_for_node("extracted_csv_files")
        assert len(extracted_data) == 2  # FakeGoogleDriveResource returns 2 files
        
        # Verify all checks passed
        check_evaluations = result.get_asset_check_evaluations()
        for evaluation in check_evaluations:
            assert evaluation.passed, f"Check failed: {evaluation.check_name}"
    
    def test_transformation_with_asset_checks(self):
        """Test transformation asset with integrated asset checks."""
        # Create sample extracted data
        sample_data = [{
            'file_name': 'test.csv',
            'dataframe': pd.DataFrame({
                'name': ['Alice', 'Bob', 'Charlie'],
                'age': [25, 30, 35],
                'city': ['NYC', 'LA', 'SF']
            }),
            'row_count': 3,
            'column_count': 3,
            'parse_info': {'separator': ',', 'encoding': 'utf-8'}
        }]
        
        # Build context and materialize
        context = build_asset_context()
        result = transformed_csv_files(context, sample_data)
        
        # Now run the checks on the result
        structure_check = check_column_normalization(result.value)
        quality_check = check_transformation_quality(result.value)
        
        # Verify checks passed
        assert structure_check.passed
        assert quality_check.passed
        assert "normalized" in structure_check.description.lower()
    
    def test_individual_asset_check(self):
        """Test running an individual asset check."""
        # Create test data
        test_data = [{
            'file_name': 'test.csv',
            'dataframe': pd.DataFrame({'COL1': [1, 2], 'COL2': [3, 4]}),
            'row_count': 2,
            'column_count': 2,
            'parse_info': {'separator': ',', 'encoding': 'utf-8'}
        }]
        
        # Run the check directly
        check_result = check_extracted_files_structure(test_data)
        
        # Verify
        assert check_result.passed
        assert check_result.metadata is not None
        assert "files_checked" in check_result.metadata
    
    def test_asset_check_failure_detection(self):
        """Test that asset checks properly detect failures."""
        # Create invalid data (missing required keys)
        invalid_data = [{
            'file_name': 'test.csv',
            # Missing 'dataframe' key!
        }]
        
        # Run the check
        check_result = check_extracted_files_structure(invalid_data)
        
        # Verify it fails
        assert not check_result.passed
        assert "missing keys" in check_result.description.lower()
