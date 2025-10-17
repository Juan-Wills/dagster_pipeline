# Updated Pipeline Architecture - Multi-File CSV Processing

## Overview
This pipeline processes **ANY CSV files** from Google Drive through a complete ETL workflow: extraction, transformation, upload to Google Drive, and loading into DuckDB.

---

## Pipeline Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      MULTI-FILE CSV PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────┐
│    Google Drive                  │
│    raw_data folder               │
│    - file1.csv                   │
│    - file2.csv                   │
│    - 002_victims.csv             │
│    - any_other_file.csv          │
└────────────┬─────────────────────┘
             │
             │ Step 1: Extract ALL CSV files
             │ (Download to memory, parse with sep='»')
             ↓
┌─────────────────────────────────────────┐
│  extracted_csv_files                    │
│  Asset 1: List[Dict]                    │
│  [                                      │
│    {                                    │
│      'file_name': 'file1.csv',          │
│      'dataframe': DataFrame,            │
│      'row_count': 1000,                 │
│      'column_count': 25                 │
│    },                                   │
│    {...}, {...}                         │
│  ]                                      │
└────────────┬────────────────────────────┘
             │
             │ Step 2: Transform ALL files
             │ (Clean, normalize, fill missing)
             ↓
┌─────────────────────────────────────────┐
│  transformed_csv_files                  │
│  Asset 2: List[Dict]                    │
│  [                                      │
│    {                                    │
│      'original_file_name': 'file1.csv', │
│      'output_file_name':                │
│         'file1_transformed.csv',        │
│      'dataframe': DataFrame,            │
│      'row_count': 950,                  │
│      'column_count': 20                 │
│    },                                   │
│    {...}, {...}                         │
│  ]                                      │
└────────────┬────────────────────────────┘
             │
             │ Step 3: Upload ALL to Google Drive
             │ (Convert to CSV with sep='|', upload from memory)
             ↓
┌─────────────────────────────────────────┐
│  upload_transformed_csv_files           │
│  Asset 3: List[str]                     │
│  [                                      │
│    'file1_transformed.csv',             │
│    'file2_transformed.csv',             │
│    '002_victims_transformed.csv'        │
│  ]                                      │
└────────────┬────────────────────────────┘
             │
             │ ✓ Upload Complete!
             │
             │ Step 4: Load to DuckDB
             │ (Only runs AFTER upload finishes)
             ↓
┌─────────────────────────────────────────┐
│  load_csv_files_to_duckdb               │
│  Asset 4: List[Dict]                    │
│  [                                      │
│    {                                    │
│      'table_name': 'file1_transformed', │
│      'source_file': 'file1_trans...csv',│
│      'row_count': 950,                  │
│      'column_count': 20                 │
│    },                                   │
│    {...}, {...}                         │
│  ]                                      │
└────────────┬────────────────────────────┘
             │
             ↓
┌──────────────────────────────────┐
│    DuckDB Tables Created:        │
│    - file1_transformed           │
│    - file2_transformed           │
│    - 002_victims_transformed     │
└──────────────────────────────────┘

     AND

┌──────────────────────────────────┐
│    Google Drive                  │
│    processed_data folder         │
│    - file1_transformed.csv       │
│    - file2_transformed.csv       │
│    - 002_victims_transformed.csv │
└──────────────────────────────────┘
```

---

## Asset Details

### Asset 1: `extracted_csv_files`
**Purpose**: Extract ALL CSV files from Google Drive  
**Input**: GoogleDriveResource  
**Output**: `List[Dict]` containing DataFrames and metadata

**Process**:
1. Finds `raw_data` folder in Google Drive
2. Lists ALL CSV files (no filtering by name)
3. For each file:
   - Downloads content to memory (BytesIO)
   - Parses with `sep='»'`, `encoding='ISO-8859-1'`
   - Creates dict with file metadata and DataFrame

**Output Structure**:
```python
[
    {
        'file_name': 'original.csv',
        'dataframe': pd.DataFrame,
        'row_count': 1000,
        'column_count': 25
    },
    # ... more files
]
```

**Metadata Logged**:
- `files_extracted`: Number of files processed
- `total_rows`: Sum of rows across all files
- `file_names`: List of all file names

---

### Asset 2: `transformed_csv_files`
**Purpose**: Transform ALL extracted DataFrames  
**Input**: `extracted_csv_files` (List[Dict])  
**Output**: `List[Dict]` with transformed DataFrames

**Transformations Applied** (to each file):
1. **Column Normalization**: UPPERCASE all column names
2. **Quality Checks**:
   - Remove columns with >90% missing values
   - Remove constant columns (nunique <= 1)
3. **String Cleaning**:
   - Strip whitespace
   - Collapse multiple spaces to single space
   - Convert to UPPERCASE
   - Replace null-like values ('nan', 'None', '', ' ') with 'NA'
4. **Missing Value Handling**:
   - String columns → 'NA'
   - Numeric columns → 0

**Output Structure**:
```python
[
    {
        'original_file_name': 'file.csv',
        'output_file_name': 'file_transformed.csv',
        'dataframe': pd.DataFrame,
        'row_count': 950,
        'column_count': 20
    },
    # ... more files
]
```

**Metadata Logged**:
- `files_transformed`: Number of files transformed
- `total_rows`: Sum of rows across all files
- `file_names`: List of output file names

---

### Asset 3: `upload_transformed_csv_files`
**Purpose**: Upload ALL transformed files to Google Drive  
**Input**: `transformed_csv_files` (List[Dict])  
**Output**: `List[str]` (uploaded file names)

**Process**:
1. Creates/finds `processed_data` folder in Google Drive
2. For each transformed DataFrame:
   - Converts to CSV in memory (BytesIO)
   - Settings: `sep='|'`, `encoding='utf-8'`, `index=False`
   - Uploads using `upload_file_from_memory()`
3. Returns list of successfully uploaded file names

**File Naming**:
- Original: `002_victims.csv` → Output: `002_victims_transformed.csv`
- Original: `data.csv` → Output: `data_transformed.csv`

**Metadata Logged**:
- `files_uploaded`: Number of successful uploads
- `file_names`: List of uploaded file names
- `total_rows`: Total rows across all files

---

### Asset 4: `load_csv_files_to_duckdb`
**Purpose**: Load ALL transformed DataFrames into DuckDB  
**Input**: 
- `transformed_csv_files` (List[Dict])
- `upload_transformed_csv_files` (List[str]) ← **Dependency ensures upload completes first**
**Output**: `List[Dict]` with load statistics

**Process**:
1. **Waits** for Google Drive upload to complete (dependency)
2. For each transformed DataFrame:
   - Sanitizes file name to create table name:
     - `002_victims_transformed.csv` → `002_victims_transformed`
     - Replaces special chars with `_`
     - Converts to lowercase
   - Registers DataFrame as temp view
   - Executes: `CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM temp_view`
   - Verifies row and column counts

**Table Naming Examples**:
- `file1_transformed.csv` → table: `file1_transformed`
- `002_victims_transformed.csv` → table: `002_victims_transformed`
- `my-data.csv` → table: `my_data`

**Metadata Logged**:
- `tables_created`: Number of tables created
- `table_names`: List of table names
- `total_rows_loaded`: Total rows inserted
- `status`: 'success'

---

## Key Features

### ✅ **Works with ANY CSV Files**
- No hardcoding of file names
- Processes all CSVs found in `raw_data` folder
- Handles variable number of files

### ✅ **100% In-Memory Processing**
- Download: BytesIO stream
- Transform: pandas DataFrame operations
- Upload: BytesIO stream
- No temporary files on disk

### ✅ **Guaranteed Execution Order**
```
Extract → Transform → Upload → Load to DuckDB
                        ↓
                   (Must complete before DuckDB load)
```

### ✅ **Dual Output Storage**
1. **Google Drive**: CSV files with `|` separator (UTF-8)
2. **DuckDB**: Queryable tables for analytics

### ✅ **Comprehensive Metadata**
- Each asset returns detailed metadata
- Full observability at every step
- Easy debugging and monitoring

### ✅ **Automatic Table Naming**
- File names automatically converted to valid table names
- Special characters sanitized
- Collision-free naming

---

## Configuration Requirements

### Resources
```python
# Google Drive Resource
google_drive = GoogleDriveResource(
    credentials_path="auth/credentials.json",
    token_path="auth/token.json",
    scopes=["https://www.googleapis.com/auth/drive"]
)

# DuckDB Resource
duckdb = DuckDBResource(
    database="data/duckdb/prueba.duckdb"
)
```

### Google Drive Folder Structure
```
Google Drive Root/
├── raw_data/
│   ├── file1.csv
│   ├── file2.csv
│   ├── 002_victims.csv
│   └── any_other.csv
│
└── processed_data/          ← Created by pipeline
    ├── file1_transformed.csv
    ├── file2_transformed.csv
    ├── 002_victims_transformed.csv
    └── any_other_transformed.csv
```

---

## Running the Pipeline

### Method 1: Run All Assets (Dagster UI)
1. Start Dagster: `dagster dev`
2. Navigate to Assets
3. Select all assets in the pipeline
4. Click "Materialize selected"

### Method 2: Run Individual Assets
```python
# In Dagster UI, materialize assets one by one:
# 1. extracted_csv_files
# 2. transformed_csv_files
# 3. upload_transformed_csv_files
# 4. load_csv_files_to_duckdb
```

### Asset Dependency Graph
```
extracted_csv_files (independent - starts the pipeline)
    ↓
transformed_csv_files (depends on: extracted_csv_files)
    ↓
    ├── upload_transformed_csv_files (depends on: transformed_csv_files)
    │       ↓
    └── load_csv_files_to_duckdb (depends on: transformed_csv_files, upload_transformed_csv_files)
```

**Note**: `load_csv_files_to_duckdb` has TWO dependencies:
1. `transformed_csv_files` - provides the data
2. `upload_transformed_csv_files` - ensures upload completes first

---

## Example Execution

### Input Files in Google Drive `raw_data/`:
```
- employees.csv (1000 rows, 30 columns)
- 002_victims.csv (500 rows, 25 columns)
- sales_data.csv (5000 rows, 15 columns)
```

### Pipeline Execution:

**Step 1**: Extract
- Downloads 3 files to memory
- Parses with `sep='»'`, `encoding='ISO-8859-1'`
- Total: 6500 rows extracted

**Step 2**: Transform
- Cleans all 3 DataFrames
- Removes high-missing columns
- Normalizes strings
- Total: ~6200 rows after cleaning (some rows removed)

**Step 3**: Upload to Google Drive
- Creates 3 new files in `processed_data/`:
  - `employees_transformed.csv`
  - `002_victims_transformed.csv`
  - `sales_data_transformed.csv`
- All with `sep='|'`, `encoding='utf-8'`

**Step 4**: Load to DuckDB
- Creates 3 tables:
  - `employees_transformed` (950 rows)
  - `002_victims_transformed` (480 rows)
  - `sales_data_transformed` (4800 rows)
- Total: 6230 rows loaded

---

## Error Handling

### Google Drive Errors
- **Missing `raw_data` folder**: Pipeline raises `ValueError` with clear message
- **No CSV files found**: Pipeline raises `ValueError`
- **Upload failures**: Logged per file, doesn't stop other uploads

### Transformation Errors
- All exceptions logged with file context
- Pipeline fails fast to prevent bad data propagation

### Database Errors
- Connection failures: Logged and re-raised
- Table creation failures: Logged and re-raised
- Individual file failures don't affect others

---

## Monitoring & Observability

### Dagster UI Shows:
1. **Asset lineage**: Visual graph of dependencies
2. **Metadata per run**:
   - Files processed
   - Rows processed
   - Tables created
   - Upload status
3. **Logs**: Detailed per-file progress
4. **Run history**: Track success/failure over time

### Key Metrics to Monitor:
- Files extracted vs files loaded (should match)
- Rows before/after transformation (data quality check)
- Upload success rate
- DuckDB table creation success

---

## Differences from Previous Version

### Before (Victims-Only Pipeline):
- ❌ Hardcoded to process only victims files
- ❌ Single DataFrame processing
- ❌ DuckDB load ran in parallel with upload
- ❌ Fixed table name (`victims`)

### After (Multi-File Pipeline):
- ✅ Processes ALL CSV files dynamically
- ✅ List-based processing for multiple files
- ✅ DuckDB load waits for upload completion
- ✅ Dynamic table names from file names
- ✅ Scalable to any number of files

---

## File Structure

```
dagster_pipeline/
├── assets/
│   ├── prueba.py              ← Main pipeline (4 assets)
│   │   ├── extracted_csv_files
│   │   ├── transformed_csv_files
│   │   ├── upload_transformed_csv_files
│   │   └── load_csv_files_to_duckdb
│   │
│   └── google_drive_etl.py    ← Utility file (no download assets)
│
├── resources/
│   ├── google_drive_resource.py
│   └── duckdb_connection.py
│
└── docs/
    └── UPDATED_PIPELINE_ARCHITECTURE.md  ← This file
```

---

## Future Enhancements

### Potential Improvements:
1. **Incremental Processing**: Only process new/changed files
2. **File Filtering**: Add configuration to include/exclude patterns
3. **Custom Transformations**: Per-file transformation rules
4. **Data Validation**: Schema validation before loading
5. **Partitioning**: Process files by date/category
6. **Archiving**: Move processed files to archive folder
7. **Notifications**: Email/Slack alerts on completion
8. **Retry Logic**: Automatic retry on transient failures

---

**Last Updated**: October 17, 2025  
**Version**: 3.0 (Multi-File Processing with Sequential Load)  
**Status**: Production Ready ✅
