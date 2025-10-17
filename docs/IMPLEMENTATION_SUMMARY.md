# Dagster Sensor Implementation Summary

## ✅ What Was Created

### 1. **Google Drive Resource** 
   - **File**: `pipeline/resources/google_drive_resource.py`
   - **Purpose**: Wraps Google Drive API for Dagster
   - **Key Features**:
     - Authentication handling
     - Folder search and creation
     - File upload/download
     - File listing with metadata

### 2. **ETL Asset**
   - **File**: `pipeline/assets/google_drive_etl.py`
   - **Asset Name**: `process_drive_files`
   - **Purpose**: Downloads files from raw_data, processes them, uploads to processed_data
   - **Current Processing**: Pass-through (copy files as-is)
   - **Ready for**: Adding pandas, transformations, validation, etc.

### 3. **File Monitor Sensor**
   - **File**: `pipeline/sensors/sensors.py`
   - **Sensor Name**: `google_drive_new_file_sensor`
   - **Purpose**: Monitors Google Drive for new CSV files
   - **Trigger**: Runs asset when new files detected
   - **Frequency**: Every 60 seconds
   - **State Management**: Uses cursor to track seen files

### 4. **Configuration**
   - **File**: `pipeline/definitions.py`
   - **Combines**: Assets, Resources, and Sensors
   - **Configures**: Google Drive credentials path

## 🔄 How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  Google Drive "raw_data" Folder                             │
│  📁 Contains: employee.csv, sales.csv, etc.                 │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  🔍 SENSOR: google_drive_new_file_sensor                    │
│  • Checks every 60 seconds                                  │
│  • Lists all CSV files in raw_data                          │
│  • Compares with cursor (previously seen files)             │
│  • Detects: new_files = current_files - seen_files          │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   │ New files detected?
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  ⚡ TRIGGER: RunRequest                                     │
│  • Creates run with tags (file names, count)                │
│  • Updates cursor with new file IDs                         │
│  • Triggers asset materialization                           │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  🏭 ASSET: process_drive_files                              │
│                                                               │
│  Step 1: Download                                            │
│    • Connects to Google Drive                                │
│    • Downloads all CSV files from raw_data                   │
│    • Saves to: downloaded_csv/                               │
│                                                               │
│  Step 2: Process (Currently: Pass-through)                   │
│    • Reads file from downloaded_csv/                         │
│    • [Your processing logic here]                            │
│    • Writes to: processed_data/                              │
│                                                               │
│  Step 3: Upload                                              │
│    • Creates/finds processed_data folder in Drive            │
│    • Uploads processed files to Drive                        │
│    • Returns metadata (file count, names)                    │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Google Drive "processed_data" Folder                        │
│  📁 Contains: processed files                                │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Sensor State Management

The sensor uses a **cursor** to track which files have been processed:

```json
{
  "file_ids": ["1abc", "2def", "3ghi"],
  "last_check": "2025-10-16T10:30:00"
}
```

- **First run**: Cursor is empty → all files are "new"
- **Subsequent runs**: Only files not in cursor are "new"
- **After processing**: Cursor is updated with all current file IDs

## 🎯 Key Features

### Idempotency
- Sensor tracks processed files via cursor
- Won't reprocess the same file unless cursor is reset
- Safe to run multiple times

### Monitoring
- Dagster UI shows sensor status
- Run history with logs
- Metadata on each run (file names, counts)

### Error Handling
- Skips execution if raw_data folder not found
- Logs errors for individual file uploads
- Continues processing even if one file fails

### Scalability
- Processes all new files in a single run
- Can handle multiple files detected simultaneously
- Configurable check interval

## 🔧 Customization Points

### 1. Processing Logic
**Location**: `pipeline/assets/google_drive_etl.py` (line ~64)

Add your transformations:
```python
import pandas as pd

# Read CSV
df = pd.read_csv(local_path)

# Your transformations
df = df.dropna()
df['new_column'] = df['old_column'] * 2
df = df[df['value'] > 100]

# Save processed
df.to_csv(processed_path, index=False)
```

### 2. Sensor Frequency
**Location**: `pipeline/sensors/sensors.py` (line ~14)

```python
@sensor(
    minimum_interval_seconds=300,  # 5 minutes
    ...
)
```

### 3. File Types
**Location**: `pipeline/sensors/sensors.py` (line ~36)

```python
# Change from CSV to JSON
files = google_drive.list_files_in_folder(
    raw_folder_id, 
    mime_type='application/json'
)
```

### 4. Folder Names
**Location**: `pipeline/sensors/sensors.py` and `pipeline/assets/google_drive_etl.py`

Change `"raw_data"` and `"processed_data"` to your folder names.

## 📦 Dependencies

```toml
[dependency-groups]
dagster = [
    "dagster>=1.11.14",
]
google-api = [
    "google-api-python-client>=2.184.0",
    "google-auth-httplib2>=0.2.0",
    "google-auth-oauthlib>=1.2.2",
]
```

## 🚀 Getting Started

1. **Install dependencies:**
   ```bash
   pip install -e ".[dagster,google-api]"
   ```

2. **Start Dagster:**
   ```bash
   dagster dev -f pipeline/definitions.py
   ```

3. **Enable sensor in UI:**
   - Navigate to http://localhost:3000
   - Go to Sensors tab
   - Enable `google_drive_new_file_sensor`

4. **Test:**
   - Upload CSV to Google Drive "raw_data"
   - Wait 60 seconds
   - Check Runs tab for execution

## 📝 Next Steps

1. **Add processing logic** in the asset
2. **Add data validation** (e.g., schema checks)
3. **Add notifications** (Slack, email) on success/failure
4. **Add more sensors** for different folders or file types
5. **Add schedules** for regular processing
6. **Connect to database** for storing metadata
7. **Add tests** for your processing logic

## 🐛 Common Issues

1. **ModuleNotFoundError**: Install dependencies with pip
2. **Authentication failed**: Delete `token.json` and re-authenticate
3. **Folder not found**: Create "raw_data" folder in Google Drive
4. **Sensor not triggering**: Make sure it's enabled in Dagster UI
5. **Files not detected**: Check they're CSV files in the root of raw_data
