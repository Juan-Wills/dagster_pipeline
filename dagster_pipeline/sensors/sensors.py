"""Sensors for the pipeline

Define sensors that watch for external events and start jobs.
"""

import json
from datetime import datetime
from dagster import sensor, RunRequest, SkipReason, SensorEvaluationContext, AssetSelection
from dagster_pipeline.resources.google_drive_resource import GoogleDriveResource


@sensor(
    name="google_drive_new_file_sensor",
    asset_selection=AssetSelection.assets("process_drive_files"),
    minimum_interval_seconds=60,  # Check every 60 seconds
    description="Monitors Google Drive raw_data folder for new CSV files"
)
def google_drive_new_file_sensor(
    context: SensorEvaluationContext,
    google_drive: GoogleDriveResource
):
    """
    Sensor that checks for new files in Google Drive raw_data folder.
    Triggers the process_drive_files asset when new files are detected.
    """
    
    # Find raw_data folder
    raw_folder_id = google_drive.find_folder_by_name("raw_data")
    
    if not raw_folder_id:
        context.log.error("'raw_data' folder not found in Google Drive")
        return SkipReason("raw_data folder not found")
    
    # List all CSV files in the folder
    files = google_drive.list_files_in_folder(raw_folder_id, mime_type='text/csv')
    
    if not files:
        return SkipReason("No CSV files in raw_data folder")
    
    # Get cursor (last processed state)
    cursor_dict = json.loads(context.cursor) if context.cursor else {}
    last_seen_files = set(cursor_dict.get("file_ids", []))
    
    # Get current file IDs
    current_file_ids = {file['id'] for file in files}
    
    # Check for new files
    new_file_ids = current_file_ids - last_seen_files
    
    if not new_file_ids:
        return SkipReason(f"No new files detected. Still monitoring {len(files)} file(s).")
    
    # Get details of new files
    new_files = [f for f in files if f['id'] in new_file_ids]
    new_file_names = [f['name'] for f in new_files]
    
    context.log.info(f"Detected {len(new_files)} new file(s): {', '.join(new_file_names)}")
    
    # Current timestamp
    current_time = datetime.now()
    
    # Update cursor with all current files
    new_cursor = json.dumps({
        "file_ids": list(current_file_ids),
        "last_check": current_time.isoformat()
    })
    
    # Trigger the asset materialization
    yield RunRequest(
        run_key=f"new_files_{current_time.timestamp()}",
        run_config={},
        tags={
            "new_files": ",".join(new_file_names),
            "file_count": str(len(new_files))
        }
    )
    
    # Update cursor
    context.update_cursor(new_cursor)


