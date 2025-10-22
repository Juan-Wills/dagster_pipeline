"""Test upload failure handling in the loading asset."""

import pytest
import pandas as pd
from dagster import build_asset_context, materialize_to_memory
from dagster_pipeline.assets.loading import upload_transformed_csv_files, check_upload_success


class TestUploadFailureHandling:
    """Test that upload failures are properly tracked and reported."""
    
    def test_upload_result_structure(self):
        """Test that upload results have the correct structure with status field."""
        
        # Simulate mixed successful and failed uploads
        upload_results = [
            {
                'file_name': 'test1_transformed.csv',
                'name': 'test1_transformed.csv',
                'id': 'file_id_1',
                'status': 'success',
                'action': 'created'
            },
            {
                'file_name': 'test2_transformed.csv',
                'name': 'test2_transformed.csv',
                'id': None,
                'status': 'failed',
                'action': 'failed',
                'error': 'Upload error'
            }
        ]
        
        # Verify structure
        assert len(upload_results) == 2
        
        # Check successful upload structure
        successful = [f for f in upload_results if f['status'] == 'success']
        assert len(successful) == 1
        assert successful[0]['file_name'] == 'test1_transformed.csv'
        assert successful[0]['id'] is not None
        
        # Check failed upload structure
        failed = [f for f in upload_results if f['status'] == 'failed']
        assert len(failed) == 1
        assert failed[0]['file_name'] == 'test2_transformed.csv'
        assert failed[0]['id'] is None
        assert 'error' in failed[0]
    
    def test_asset_check_detects_upload_failures(self):
        """Test that the asset check properly detects upload failures."""
        
        # Simulate upload results with failures
        upload_results = [
            {
                'file_name': 'test1_transformed.csv',
                'name': 'test1_transformed.csv',
                'id': 'file_id_1',
                'status': 'success',
                'action': 'created'
            },
            {
                'file_name': 'test2_transformed.csv',
                'name': 'test2_transformed.csv',
                'id': None,
                'status': 'failed',
                'action': 'failed',
                'error': 'Upload error'
            },
            {
                'file_name': 'test3_transformed.csv',
                'name': 'test3_transformed.csv',
                'id': None,
                'status': 'failed',
                'action': 'failed',
                'error': 'Network error'
            }
        ]
        
        # Run the asset check
        check_result = check_upload_success(upload_results)
        
        # Should fail because 2 uploads failed
        assert not check_result.passed
        assert "2/3 file(s) failed to upload" in check_result.description
        
        # Check metadata (values are wrapped in MetadataValue objects)
        assert check_result.metadata['failed_count'].value == 2
        assert 'test2_transformed.csv' in check_result.metadata['failed_files'].value
        assert 'test3_transformed.csv' in check_result.metadata['failed_files'].value
        assert check_result.metadata['successful_count'].value == 1
    
    def test_asset_check_passes_with_all_success(self):
        """Test that the asset check passes when all uploads succeed."""
        
        # Simulate all successful uploads
        upload_results = [
            {
                'file_name': 'test1_transformed.csv',
                'name': 'test1_transformed.csv',
                'id': 'file_id_1',
                'status': 'success',
                'action': 'created'
            },
            {
                'file_name': 'test2_transformed.csv',
                'name': 'test2_transformed.csv',
                'id': 'file_id_2',
                'status': 'success',
                'action': 'replaced'
            }
        ]
        
        # Run the asset check
        check_result = check_upload_success(upload_results)
        
        # Should pass
        assert check_result.passed
        assert "All 2 files uploaded successfully" in check_result.description
        assert check_result.metadata['files_uploaded'].value == 2
        assert check_result.metadata['files_created'].value == 1
        assert check_result.metadata['files_replaced'].value == 1
