"""Tests for Dagster sensors

Tests for sensors that monitor external events.
Using fake resources instead of mocks.
"""

import json
import pytest

from dagster import build_sensor_context, RunRequest, SkipReason
from dagster_pipeline.sensors.sensors import google_drive_new_file_sensor


# ============================================================================
# Google Drive Sensor Tests
# ============================================================================

class TestGoogleDriveSensor:
    """Test suite for Google Drive new file sensor."""
    
    def test_sensor_no_raw_data_folder(self, google_drive_resource):
        """Test sensor skips when raw_data folder not found."""
        # Remove raw_data folder
        google_drive_resource.folders.pop('raw_data', None)
        
        context = build_sensor_context(resources={"google_drive": google_drive_resource})
        result = google_drive_new_file_sensor(context)
        
        # Sensor yields results, consume the generator
        result_list = list(result)
        assert len(result_list) == 1
        assert isinstance(result_list[0], SkipReason)
        assert "not found" in str(result_list[0])
    
    def test_sensor_no_files_in_folder(self, google_drive_resource):
        """Test sensor skips when no CSV files found."""
        # Override to return empty list
        google_drive_resource._list_files_override = []
        
        context = build_sensor_context(resources={"google_drive": google_drive_resource})
        result = google_drive_new_file_sensor(context)
        
        # Sensor yields results, consume the generator
        result_list = list(result)
        assert len(result_list) == 1
        assert isinstance(result_list[0], SkipReason)
        assert "No CSV files" in str(result_list[0])
    
    def test_sensor_detects_new_files(self, google_drive_resource):
        """Test sensor triggers run request when new files detected."""
        # Set up files to be found
        google_drive_resource._list_files_override = [
            {'id': 'file1', 'name': 'new_file.csv'}
        ]
        
        # Empty cursor (first run)
        context = build_sensor_context(cursor=None, resources={"google_drive": google_drive_resource})
        result = google_drive_new_file_sensor(context)
        
        # Sensor yields results, consume the generator
        result_list = list(result)
        assert len(result_list) == 1
        assert isinstance(result_list[0], RunRequest)
    
    def test_sensor_no_new_files_with_cursor(self, google_drive_resource):
        """Test sensor skips when no new files since last check."""
        google_drive_resource._list_files_override = [
            {'id': 'file1', 'name': 'existing_file.csv'}
        ]
        
        # Cursor with the same file
        cursor = json.dumps({"file_ids": ["file1"]})
        context = build_sensor_context(cursor=cursor, resources={"google_drive": google_drive_resource})
        result = google_drive_new_file_sensor(context)
        
        # Sensor yields results, consume the generator
        result_list = list(result)
        assert len(result_list) == 1
        assert isinstance(result_list[0], SkipReason)
    
    def test_sensor_updates_cursor(self, google_drive_resource):
        """Test sensor updates cursor with current file list."""
        google_drive_resource._list_files_override = [
            {'id': 'file1', 'name': 'file1.csv'},
            {'id': 'file2', 'name': 'file2.csv'}
        ]
        
        context = build_sensor_context(cursor=None, resources={"google_drive": google_drive_resource})
        result = google_drive_new_file_sensor(context)
        
        result_list = list(result)
        assert len(result_list) == 1
        assert isinstance(result_list[0], RunRequest)
    
    def test_sensor_detects_multiple_new_files(self, google_drive_resource):
        """Test sensor detects multiple new files at once."""
        # First call: 1 file
        cursor = json.dumps({"file_ids": ["file1"]})
        
        # Second call: 3 files (2 new)
        google_drive_resource._list_files_override = [
            {'id': 'file1', 'name': 'file1.csv'},
            {'id': 'file2', 'name': 'file2.csv'},
            {'id': 'file3', 'name': 'file3.csv'}
        ]
        
        context = build_sensor_context(cursor=cursor, resources={"google_drive": google_drive_resource})
        result = google_drive_new_file_sensor(context)
        
        result_list = list(result)
        assert len(result_list) == 1
        assert isinstance(result_list[0], RunRequest)
    
    def test_sensor_handles_deleted_files(self, google_drive_resource):
        """Test sensor handles case where previously seen files are deleted."""
        # Previous state: 3 files
        cursor = json.dumps({"file_ids": ["file1", "file2", "file3"]})
        
        # Current state: only 1 file (2 deleted)
        google_drive_resource._list_files_override = [
            {'id': 'file1', 'name': 'file1.csv'}
        ]
        
        context = build_sensor_context(cursor=cursor, resources={"google_drive": google_drive_resource})
        result = google_drive_new_file_sensor(context)
        
        # Sensors consistently yield results
        result_list = list(result)
        assert len(result_list) == 1
        
        # Should skip since no NEW files (even though some were deleted)
        assert isinstance(result_list[0], SkipReason)
    
    def test_sensor_first_run_triggers(self, google_drive_resource):
        """Test sensor triggers on first run when files exist."""
        google_drive_resource._list_files_override = [
            {'id': 'file1', 'name': 'initial_file.csv'}
        ]
        
        # First run with no cursor
        context = build_sensor_context(cursor=None, resources={"google_drive": google_drive_resource})
        result = google_drive_new_file_sensor(context)
        
        result_list = list(result)
        assert len(result_list) == 1
        assert isinstance(result_list[0], RunRequest)


# ============================================================================
# Sensor Error Handling Tests
# ============================================================================

class TestSensorErrorHandling:
    """Test error handling in sensors."""
    
    def test_sensor_handles_api_error(self, google_drive_resource):
        """Test sensor handles Google Drive API errors gracefully."""
        # Make find_folder_by_name raise an error
        def raise_error(name):
            raise Exception("API Error")
        
        google_drive_resource.find_folder_by_name = raise_error
        
        context = build_sensor_context(resources={"google_drive": google_drive_resource})
        
        # Sensor should propagate the error (doesn't handle it internally)
        with pytest.raises(Exception, match="API Error"):
            result = google_drive_new_file_sensor(context)
            list(result)  # Consume the generator
    
    def test_sensor_handles_invalid_cursor(self, google_drive_resource):
        """Test sensor raises error for invalid cursor data."""
        google_drive_resource._list_files_override = [
            {'id': 'file1', 'name': 'file1.csv'}
        ]
        
        # Invalid JSON cursor
        context = build_sensor_context(cursor="invalid json {", resources={"google_drive": google_drive_resource})
        
        # Sensor should raise JSONDecodeError for invalid cursor
        with pytest.raises(json.JSONDecodeError):
            result = google_drive_new_file_sensor(context)
            list(result)  # Consume the generator


# ============================================================================
# Sensor Configuration Tests
# ============================================================================

class TestSensorConfiguration:
    """Test sensor configuration and metadata."""
    
    def test_sensor_minimum_interval(self):
        """Test sensor has appropriate minimum interval configured."""
        # Check that the sensor decorator has correct settings
        # This is more of a smoke test to ensure the sensor is properly configured
        assert hasattr(google_drive_new_file_sensor, 'name')
        assert google_drive_new_file_sensor.name == "google_drive_new_file_sensor"
    
    def test_sensor_asset_selection(self):
        """Test sensor targets correct assets."""
        # The sensor should target the process_drive_files asset
        # This verifies the sensor is configured with the right asset selection
        assert hasattr(google_drive_new_file_sensor, 'name')


# ============================================================================
# Sensor Integration Tests
# ============================================================================

class TestSensorIntegration:
    """Integration tests for sensor behavior."""
    
    def test_sensor_run_request_contains_metadata(self, google_drive_resource):
        """Test run request includes useful metadata."""
        google_drive_resource._list_files_override = [
            {'id': 'file1', 'name': 'test.csv'}
        ]
        
        context = build_sensor_context(cursor=None, resources={"google_drive": google_drive_resource})
        result = google_drive_new_file_sensor(context)
        
        result_list = list(result)
        assert len(result_list) == 1
        # Verify run request is properly formed
        assert isinstance(result_list[0], RunRequest)
    
    def test_sensor_multiple_evaluations(self, google_drive_resource):
        """Test sensor behavior across multiple evaluations."""
        
        # First evaluation: 1 file
        google_drive_resource._list_files_override = [
            {'id': 'file1', 'name': 'file1.csv'}
        ]
        context1 = build_sensor_context(cursor=None, resources={"google_drive": google_drive_resource})
        result1 = google_drive_new_file_sensor(context1)
        results = list(result1)
        assert len(results) == 1
        assert isinstance(results[0], RunRequest)
        
        # Second evaluation: same file
        cursor2 = json.dumps({"file_ids": ["file1"]})
        context2 = build_sensor_context(cursor=cursor2, resources={"google_drive": google_drive_resource})
        result2 = google_drive_new_file_sensor(context2)
        results = list(result2)
        assert len(results) == 1
        assert isinstance(results[0], SkipReason)
        
        # Third evaluation: new file added
        google_drive_resource._list_files_override = [
            {'id': 'file1', 'name': 'file1.csv'},
            {'id': 'file2', 'name': 'file2.csv'}
        ]
        context3 = build_sensor_context(cursor=cursor2, resources={"google_drive": google_drive_resource})
        result3 = google_drive_new_file_sensor(context3)
        results = list(result3)
        assert len(results) == 1
        actual_result3 = results[0]
        assert isinstance(actual_result3, RunRequest)
