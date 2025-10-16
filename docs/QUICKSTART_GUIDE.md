# Google Drive Dagster Sensor - Quick Start Guide

## Prerequisites
Make sure you have Python 3.13+ installed and have your Google Drive API credentials set up.

## Installation

1. **Install dependencies:**
   ```bash
   pip install -e ".[dagster,google-api]"
   ```

   Or install manually:
   ```bash
   pip install dagster dagster-webserver google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```

2. **Verify installation:**
   ```bash
   python -c "from pipeline.definitions import defs; print('✓ Setup complete!')"
   ```

## Running the Dagster Pipeline

### Option 1: Development Mode (Recommended)
Start the Dagster development server with UI:
```bash
dagster dev -f pipeline/definitions.py
```

Then open your browser to http://localhost:3000

### Option 2: Using Dagster Daemon (Production-like)
```bash
# Start the daemon (runs sensors and schedules)
dagster-daemon run

# In another terminal, start the webserver
dagster dev -f pipeline/definitions.py
```

## Enabling the Sensor

1. Open Dagster UI at http://localhost:3000
2. Navigate to **"Automation"** → **"Sensors"** (or use the left sidebar)
3. Find **"google_drive_new_file_sensor"**
4. Click the toggle to **enable** it
5. The sensor will now check every 60 seconds for new files

## Testing the Sensor

### First Run - Initialize State
1. Make sure you have some CSV files in your Google Drive "raw_data" folder
2. The sensor will detect ALL existing files as "new" on the first run
3. It will download them and upload to "processed_data"

### Testing New File Detection
1. Upload a NEW CSV file to Google Drive "raw_data" folder
2. Wait up to 60 seconds
3. Watch the Dagster UI - the sensor should trigger
4. Check the "Runs" tab to see the execution
5. Verify the file appears in Google Drive "processed_data" folder

## Monitoring

### Check Sensor Status
- **Dagster UI** → **Sensors** tab
- Shows last tick time, status, and cursor state

### Check Run History
- **Dagster UI** → **Runs** tab
- See all triggered runs with logs and metadata

### View Asset Materializations
- **Dagster UI** → **Assets** tab
- Click on `process_drive_files` to see materialization history

## File Locations

### Local Files:
- **Downloaded files**: `downloaded_csv/`
- **Processed files**: `processed_data/`

### Google Drive:
- **Source folder**: "raw_data" (must exist)
- **Destination folder**: "processed_data" (created automatically)

## Troubleshooting

### Sensor not triggering?
1. Make sure the sensor is **enabled** in Dagster UI
2. Check that "raw_data" folder exists in Google Drive
3. Verify token.json has valid credentials
4. Check sensor logs in Dagster UI

### Authentication errors?
1. Delete `token.json`
2. Run the sensor again - it will prompt for authentication
3. Make sure `auth/credentials.json` exists and is valid

### No files detected?
1. Ensure files are in "raw_data" folder (not a subfolder)
2. Only CSV files are detected (mimeType='text/csv')
3. Check sensor cursor state - it might have already processed the files

### Clear sensor state (force reprocess all files):
In Dagster UI:
1. Go to Sensors tab
2. Click on "google_drive_new_file_sensor"
3. Click "Reset cursor" button
4. Next tick will treat all files as new

## Next Steps

### Add Data Processing
Edit `pipeline/assets/google_drive_etl.py` to add transformations:

```python
# Instead of just copying:
with open(local_path, 'rb') as src:
    with open(processed_path, 'wb') as dst:
        dst.write(src.read())

# Add pandas processing:
import pandas as pd

df = pd.read_csv(local_path)
# Your transformations here
df = df.dropna()
df = df[df['column'] > 0]
# etc...
df.to_csv(processed_path, index=False)
```

### Adjust Sensor Frequency
Edit `pipeline/sensors/sensors.py`:
```python
@sensor(
    name="google_drive_new_file_sensor",
    minimum_interval_seconds=300,  # Check every 5 minutes instead of 60 seconds
    ...
)
```

### Add Notifications
Modify the sensor to send alerts when files are processed:
```python
# In sensors.py, add Slack/email notifications
# when new files are detected
```

## Architecture Overview

```
Google Drive "raw_data"
         ↓
    [SENSOR] Checks every 60s
         ↓
   New files detected?
         ↓
  [ASSET] process_drive_files
         ↓
   Download → Process → Upload
         ↓
Google Drive "processed_data"
```

## Useful Commands

```bash
# Check Dagster version
dagster --version

# Validate definitions
dagster definitions validate -f pipeline/definitions.py

# List all assets
dagster asset list -f pipeline/definitions.py

# List all sensors
dagster sensor list -f pipeline/definitions.py

# Materialize asset manually (bypass sensor)
dagster asset materialize -f pipeline/definitions.py -a process_drive_files
```
