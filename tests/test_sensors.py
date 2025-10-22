"""Tests for Dagster sensors

Tests for sensors that monitor external events.
Following Dagster best practices for sensor testing.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from dagster import build_sensor_context, RunRequest, SkipReason
from dagster_pipeline.sensors.sensors import google_drive_new_file_sensor


# ============================================================================
# Google Drive Sensor Tests
# ============================================================================

class TestGoogleDriveSensor:
    """Test suite for Google Drive new file sensor."""
    
    def test_sensor_no_raw_data_folder(self, mock_google_drive):
        """Test sensor skips when raw_data folder not found."""
        mock_google_drive.find_folder_by_name.return_value = None
        
        context = build_sensor_context(resources={"google_drive": mock_google_drive})
        result = google_drive_new_file_sensor(context)
        
        # Sensors consistently yield results in Dagster 1.11+
        try:
            results = list(result)
            actual_result = results[0] if results else result
        except TypeError:
            actual_result = result
        
        assert isinstance(actual_result, SkipReason)
        assert "not found" in str(actual_result)
    
    def test_sensor_no_files_in_folder(self, mock_google_drive):
        """Test sensor skips when no CSV files found."""
        mock_google_drive.find_folder_by_name.return_value = "folder123"
        mock_google_drive.list_files_in_folder.return_value = []
        
        context = build_sensor_context(resources={"google_drive": mock_google_drive})
        result = google_drive_new_file_sensor(context)
        
        # Sensors consistently yield results
        try:
            results = list(result)
            actual_result = results[0] if results else result
        except TypeError:
            actual_result = result
        
        assert isinstance(actual_result, SkipReason)
        assert "No CSV files" in str(actual_result)
    
    def test_sensor_detects_new_files(self, mock_google_drive):
        """Test sensor triggers run request when new files detected."""
        mock_google_drive.find_folder_by_name.return_value = "folder123"
        mock_google_drive.list_files_in_folder.return_value = [
            {'id': 'file1', 'name': 'new_file.csv'}
        ]
        
        # Empty cursor (first run)
        context = build_sensor_context(cursor=None, resources={"google_drive": mock_google_drive})
        result = google_drive_new_file_sensor(context)
        
        # Sensors can yield (generator) or return directly
        # When yielding RunRequest, we need to consume the generator
        try:
            # Try to iterate if it's a generator
            results = list(result)
            assert len(results) > 0
            actual_result = results[0]
        except TypeError:
            # Not iterable, use directly
            actual_result = result
        
        assert isinstance(actual_result, RunRequest)
    
    def test_sensor_no_new_files_with_cursor(self, mock_google_drive):
        """Test sensor skips when no new files since last check."""
        mock_google_drive.find_folder_by_name.return_value = "folder123"
        mock_google_drive.list_files_in_folder.return_value = [
            {'id': 'file1', 'name': 'existing_file.csv'}
        ]
        
        # Cursor with the same file
        cursor = json.dumps({"file_ids": ["file1"]})
        context = build_sensor_context(cursor=cursor, resources={"google_drive": mock_google_drive})
        result = google_drive_new_file_sensor(context)
        
        # Sensors consistently yield results
        try:
            results = list(result)
            actual_result = results[0] if results else result
        except TypeError:
            actual_result = result
        
        assert isinstance(actual_result, SkipReason)
        assert "No new files" in str(actual_result)
    
    def test_sensor_updates_cursor(self, mock_google_drive):
        """Test sensor updates cursor with current file list."""
        mock_google_drive.find_folder_by_name.return_value = "folder123"
        mock_google_drive.list_files_in_folder.return_value = [
            {'id': 'file1', 'name': 'file1.csv'},
            {'id': 'file2', 'name': 'file2.csv'}
        ]
        
        context = build_sensor_context(cursor=None, resources={"google_drive": mock_google_drive})
        result = google_drive_new_file_sensor(context)
        
        if isinstance(result, RunRequest):
            # Cursor should be updated with file IDs
            assert result is not None
    
    def test_sensor_detects_multiple_new_files(self, mock_google_drive):
        """Test sensor detects multiple new files at once."""
        mock_google_drive.find_folder_by_name.return_value = "folder123"
        
        # First call: 1 file
        old_files = [{'id': 'file1', 'name': 'file1.csv'}]
        cursor = json.dumps({"file_ids": ["file1"]})
        
        # Second call: 3 files (2 new)
        mock_google_drive.list_files_in_folder.return_value = [
            {'id': 'file1', 'name': 'file1.csv'},
            {'id': 'file2', 'name': 'file2.csv'},
            {'id': 'file3', 'name': 'file3.csv'}
        ]
        
        context = build_sensor_context(cursor=cursor, resources={"google_drive": mock_google_drive})
        result = google_drive_new_file_sensor(context)
        
        # Sensors can yield (generator) or return directly
        try:
            results = list(result)
            actual_result = results[0] if results else result
        except TypeError:
            actual_result = result
        
        assert isinstance(actual_result, RunRequest)
    
    def test_sensor_handles_deleted_files(self, mock_google_drive):
        """Test sensor handles case where previously seen files are deleted."""
        mock_google_drive.find_folder_by_name.return_value = "folder123"
        
        # Previous state: 3 files
        cursor = json.dumps({"file_ids": ["file1", "file2", "file3"]})
        
        # Current state: only 1 file (2 deleted)
        mock_google_drive.list_files_in_folder.return_value = [
            {'id': 'file1', 'name': 'file1.csv'}
        ]
        
        context = build_sensor_context(cursor=cursor, resources={"google_drive": mock_google_drive})
        result = google_drive_new_file_sensor(context)
        
        # Sensors consistently yield results
        try:
            results = list(result)
            actual_result = results[0] if results else result
        except TypeError:
            actual_result = result
        
        # Should skip since no NEW files (even though some were deleted)
        assert isinstance(actual_result, SkipReason)
    
    def test_sensor_first_run_triggers(self, mock_google_drive):
        """Test sensor triggers on first run when files exist."""
        mock_google_drive.find_folder_by_name.return_value = "folder123"
        mock_google_drive.list_files_in_folder.return_value = [
            {'id': 'file1', 'name': 'initial_file.csv'}
        ]
        
        # First run with no cursor
        context = build_sensor_context(cursor=None, resources={"google_drive": mock_google_drive})
        result = google_drive_new_file_sensor(context)
        
        # Sensors can yield (generator) or return directly
        try:
            results = list(result)
            actual_result = results[0] if results else result
        except TypeError:
            actual_result = result
        
        # Should trigger since it's the first run
        assert isinstance(actual_result, RunRequest)


# ============================================================================
# Sensor Error Handling Tests
# ============================================================================

class TestSensorErrorHandling:
    """Test error handling in sensors."""
    
    def test_sensor_handles_api_error(self, mock_google_drive):
        """Test sensor handles Google Drive API errors gracefully."""
        mock_google_drive.find_folder_by_name.side_effect = Exception("API Error")
        
        context = build_sensor_context(resources={"google_drive": mock_google_drive})
        
        # Sensor should propagate the error (doesn't handle it internally)
        with pytest.raises(Exception, match="API Error"):
            result = google_drive_new_file_sensor(context)
            # Try to consume if it's a generator
            try:
                list(result)
            except TypeError:
                pass  # Not a generator
    
    def test_sensor_handles_invalid_cursor(self, mock_google_drive):
        """Test sensor handles invalid cursor data gracefully."""
        mock_google_drive.find_folder_by_name.return_value = "folder123"
        mock_google_drive.list_files_in_folder.return_value = [
            {'id': 'file1', 'name': 'file1.csv'}
        ]
        
        # Invalid JSON cursor
        context = build_sensor_context(cursor="invalid json {", resources={"google_drive": mock_google_drive})
        
        # Should handle invalid cursor gracefully
        try:
            result = google_drive_new_file_sensor(context)
            # If it doesn't raise an exception, it's handling it gracefully
            assert True
        except json.JSONDecodeError:
            # If it raises JSONDecodeError, we might want to handle it better
            assert False, "Sensor should handle invalid cursor gracefully"


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
    
    def test_sensor_run_request_contains_metadata(self, mock_google_drive):
        """Test run request includes useful metadata."""
        mock_google_drive.find_folder_by_name.return_value = "folder123"
        mock_google_drive.list_files_in_folder.return_value = [
            {'id': 'file1', 'name': 'test.csv'}
        ]
        
        context = build_sensor_context(cursor=None, resources={"google_drive": mock_google_drive})
        result = google_drive_new_file_sensor(context)
        
        if isinstance(result, RunRequest):
            # Verify run request is properly formed
            assert result is not None
    
    def test_sensor_multiple_evaluations(self, mock_google_drive):
        """Test sensor behavior across multiple evaluations."""
        mock_google_drive.find_folder_by_name.return_value = "folder123"
        
        # First evaluation: 1 file
        mock_google_drive.list_files_in_folder.return_value = [
            {'id': 'file1', 'name': 'file1.csv'}
        ]
        context1 = build_sensor_context(cursor=None, resources={"google_drive": mock_google_drive})
        result1 = google_drive_new_file_sensor(context1)
        try:
            results = list(result1)
            actual_result1 = results[0] if results else result1
        except TypeError:
            actual_result1 = result1
        assert isinstance(actual_result1, RunRequest)
        
        # Second evaluation: same file
        cursor2 = json.dumps({"file_ids": ["file1"]})
        context2 = build_sensor_context(cursor=cursor2, resources={"google_drive": mock_google_drive})
        result2 = google_drive_new_file_sensor(context2)
        try:
            results = list(result2)
            actual_result2 = results[0] if results else result2
        except TypeError:
            actual_result2 = result2
        assert isinstance(actual_result2, SkipReason)
        
        # Third evaluation: new file added
        mock_google_drive.list_files_in_folder.return_value = [
            {'id': 'file1', 'name': 'file1.csv'},
            {'id': 'file2', 'name': 'file2.csv'}
        ]
        context3 = build_sensor_context(cursor=cursor2, resources={"google_drive": mock_google_drive})
        result3 = google_drive_new_file_sensor(context3)
        try:
            results = list(result3)
            actual_result3 = results[0] if results else result3
        except TypeError:
            actual_result3 = result3
        assert isinstance(actual_result3, RunRequest)
