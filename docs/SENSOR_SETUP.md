# Google Drive Dagster Sensor Setup

## Overview
This implementation creates a Dagster sensor that monitors Google Drive's "raw_data" folder for new CSV files, downloads them, and uploads them to the "processed_data" folder.

## Components Created

### 1. Google Drive Resource (`pipeline/resources/google_drive_resource.py`)
- Handles Google Drive API authentication and operations
- Methods:
  - `find_folder_by_name()`: Find folders in Google Drive
  - `list_files_in_folder()`: List files in a specific folder
  - `download_file()`: Download files from Google Drive
  - `upload_file()`: Upload files to Google Drive
  - `create_folder_if_not_exists()`: Create folders if needed

### 2. ETL Asset (`pipeline/assets/google_drive_etl.py`)
- `process_drive_files`: Main asset that orchestrates the ETL pipeline
- Downloads CSV files from "raw_data" folder
- Currently does pass-through processing (no transformation)
- Uploads processed files to "processed_data" folder in Google Drive

### 3. Sensor (`pipeline/sensors/sensors.py`)
- `google_drive_new_file_sensor`: Monitors "raw_data" folder
- Checks every 60 seconds for new files
- Tracks file IDs using cursor to detect new files
- Triggers `process_drive_files` asset when new files are detected

## How It Works

1. **Sensor monitors** Google Drive "raw_data" folder every 60 seconds
2. **Detects new files** by comparing current file IDs with previously seen IDs (stored in cursor)
3. **Triggers the asset** when new files are detected
4. **Asset downloads** files from "raw_data" → `downloaded_csv/`
5. **Asset processes** files (currently just copies to `processed_data/`)
6. **Asset uploads** processed files to Google Drive "processed_data" folder

## Usage

### Start Dagster Development Server
```bash
cd /home/juan-wills/Documents/dagster_pipeline
dagster dev -f pipeline/definitions.py
```

### Enable the Sensor
1. Open Dagster UI (usually http://localhost:3000)
2. Go to "Sensors" tab
3. Enable "google_drive_new_file_sensor"

### Test It
1. Upload a CSV file to your Google Drive "raw_data" folder
2. Wait up to 60 seconds
3. The sensor will detect the new file and trigger the asset
4. Check the "processed_data" folder in Google Drive for the uploaded file

## File Structure
```
pipeline/
├── resources/
│   ├── google_drive_resource.py  # Google Drive API wrapper
│   └── __init__.py
├── assets/
│   ├── google_drive_etl.py       # ETL asset
│   └── __init__.py
├── sensors/
│   ├── sensors.py                # Sensor definition
│   └── __init__.py
└── definitions.py                # Main definitions file
```

## Configuration
The Google Drive resource is configured in `definitions.py`:
- `credentials_path`: Path to Google API credentials
- `token_path`: Path to store access tokens
- `scopes`: Google Drive API scopes (full drive access)

## Next Steps
To add actual data processing:
1. Modify the processing logic in `pipeline/assets/google_drive_etl.py`
2. Add transformations between download and upload
3. You can add pandas, data validation, or any other processing logic
