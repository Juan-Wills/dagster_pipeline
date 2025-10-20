# Duplicate File Handling in Google Drive Upload

## Overview

The pipeline now automatically handles duplicate files when uploading to Google Drive's `processed_data` folder. This prevents accumulation of duplicate files over multiple pipeline runs.

## Changes Made

### 1. GoogleDriveResource Enhancements

Added three new methods to `/dagster_pipeline/resources/google_drive_resource.py`:

#### `find_file_in_folder(file_name: str, folder_id: str)`
- Searches for a file by name within a specific folder
- Returns file info if found, None otherwise

#### `delete_file(file_id: str)`
- Deletes a file from Google Drive by its ID
- Used to remove old files before uploading new versions

#### Updated `upload_file()` and `upload_file_from_memory()`
- Added `replace_if_exists` parameter (default: `True`)
- When `True`: Automatically replaces existing files with the same name
- When `False`: Skips upload if file already exists
- Returns action taken: `'created'`, `'replaced'`, or `'skipped'`

### 2. Upload Asset Improvements

Updated `upload_transformed_csv_files` asset in `/dagster_pipeline/assets/google_drive_etl.py`:

- Uses `replace_if_exists=True` by default
- Tracks and logs whether files were created or replaced
- Enhanced metadata includes:
  - `files_created`: Count of newly created files
  - `files_replaced`: Count of files that replaced existing ones
  - Detailed per-file action information

## Behavior

### Default Behavior (replace_if_exists=True)
```python
# First run
uploaded = google_drive.upload_file_from_memory(
    csv_content, 
    "data.csv", 
    folder_id,
    replace_if_exists=True
)
# Result: {'action': 'created', 'id': '...', 'name': 'data.csv'}

# Second run (file already exists)
uploaded = google_drive.upload_file_from_memory(
    csv_content, 
    "data.csv", 
    folder_id,
    replace_if_exists=True
)
# Result: {'action': 'replaced', 'id': '...', 'name': 'data.csv'}
# Old file is deleted, new file uploaded
```

### Alternative Behavior (replace_if_exists=False)
```python
uploaded = google_drive.upload_file_from_memory(
    csv_content, 
    "data.csv", 
    folder_id,
    replace_if_exists=False
)
# If file exists: {'action': 'skipped', 'id': 'existing_id', 'name': 'data.csv', 'message': 'File already exists'}
```

## Logging Examples

### When Creating New Files
```
Uploading: data_transformed.csv
  ✓ Created new file: data_transformed.csv (ID: 1abc...)
```

### When Replacing Existing Files
```
Uploading: data_transformed.csv
  ✓ Replaced existing file: data_transformed.csv (ID: 1xyz...)
```

### Summary
```
Upload completed. 3 file(s) uploaded (1 new, 2 replaced)
```

## Benefits

1. **No Duplicates**: Prevents cluttering the Google Drive folder with duplicate files
2. **Always Current**: Ensures the latest version is always available
3. **Transparent**: Clear logging shows which files were created vs replaced
4. **Configurable**: Can be changed to skip uploads if needed
5. **Atomic**: Old file is only deleted after confirming new upload will succeed

## Testing

To test the duplicate handling:

1. Run the pipeline once - all files will be created
2. Run the pipeline again - all files will be replaced
3. Check the Dagster UI logs to see the action tracking
4. Verify in Google Drive that only one version of each file exists

## Future Enhancements

Possible future improvements:
- Add versioning support (keep N previous versions)
- Add timestamp suffixes for historical tracking
- Support for different strategies (replace, version, skip) per file type
