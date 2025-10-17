# Victims Data Pipeline - Implementation Summary

## Overview
This document describes the complete ETL pipeline for processing victims data from Google Drive through transformation and loading into DuckDB.

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VICTIMS DATA PIPELINE                        │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│  Google Drive        │
│  (raw_data folder)   │
│  002_victims*.csv    │
└──────────┬───────────┘
           │
           ├─── Download & Extract (in-memory)
           │    - Encoding: ISO-8859-1
           │    - Separator: '»'
           │    - No disk I/O
           ↓
┌──────────────────────┐
│ extracted_victims_df │
│  (Asset 1)           │
│  pandas DataFrame    │
└──────────┬───────────┘
           │
           ├─── Transform Data
           │    - Normalize column names (UPPERCASE)
           │    - Remove high-missing columns (>90%)
           │    - Clean strings (trim, normalize spaces)
           │    - Fill missing values (NA, 0)
           │    - Remove constant columns
           ↓
┌──────────────────────────┐
│ transformed_victims_df   │
│  (Asset 2)               │
│  pandas DataFrame        │
└──────────┬───────────────┘
           │
           ├─────────────┬──────────────┐
           │             │              │
           ↓             ↓              ↓
┌──────────────────┐  ┌──────────────────┐
│ Google Drive     │  │   DuckDB         │
│ (processed_data) │  │   victims table  │
│                  │  │                  │
│ Asset 3:         │  │  Asset 4:        │
│ upload_victims   │  │  load_victims    │
│ (CSV |sep)       │  │  (CREATE TABLE)  │
└──────────────────┘  └──────────────────┘
```

## Asset Details

### Asset 1: `extracted_victims_df`
**Type**: Extraction  
**Source**: Google Drive `raw_data` folder  
**Output**: pandas DataFrame  

**Process**:
1. Connects to Google Drive
2. Finds `raw_data` folder
3. Searches for victims CSV file (filters by 'victims' or '002' in name)
4. Downloads file content to memory (BytesIO)
5. Parses CSV with:
   - Encoding: `ISO-8859-1`
   - Separator: `'»'`
   - Engine: `python`

**Metadata Logged**:
- `file_name`: Name of the source file
- `row_count`: Number of rows loaded
- `column_count`: Number of columns
- `columns`: List of column names

---

### Asset 2: `transformed_victims_df`
**Type**: Transformation  
**Depends On**: `extracted_victims_df`  
**Output**: pandas DataFrame  

**Transformations Applied**:
1. **Column Normalization**
   - Convert all column names to UPPERCASE

2. **Data Quality Checks**
   - Remove columns with >90% missing values
   - Remove constant columns (single unique value)

3. **String Cleaning**
   - Strip leading/trailing whitespace
   - Replace multiple spaces/newlines with single space
   - Convert all text to UPPERCASE
   - Replace null-like values ('nan', 'None', '', ' ') with 'NA'

4. **Missing Value Handling**
   - String columns: Fill with 'NA'
   - Numeric columns: Fill with 0

**Metadata Logged**:
- `row_count`: Final row count
- `column_count`: Final column count
- `columns`: List of final column names

---

### Asset 3: `upload_transformed_victims_csv`
**Type**: Load (Google Drive)  
**Depends On**: `transformed_victims_df`  
**Destination**: Google Drive `processed_data` folder  
**Output**: String (uploaded file name)  

**Process**:
1. Creates/finds `processed_data` folder in Google Drive
2. Converts DataFrame to CSV in memory (BytesIO)
   - Encoding: `UTF-8`
   - Separator: `|`
   - No index column
3. Uploads to Google Drive from memory (no disk I/O)
4. File name: `victims_transformed.csv`

**Metadata Logged**:
- `file_id`: Google Drive file ID
- `file_name`: Uploaded file name
- `row_count`: Number of rows uploaded
- `column_count`: Number of columns uploaded

---

### Asset 4: `load_victims_to_duckdb`
**Type**: Load (Database)  
**Depends On**: `transformed_victims_df`  
**Destination**: DuckDB `victims` table  
**Output**: Dict with load statistics  

**Process**:
1. Connects to DuckDB
2. Registers DataFrame as temporary view `temp_victims`
3. Creates or replaces `victims` table
4. Verifies data load with row and column counts

**SQL Executed**:
```sql
CREATE OR REPLACE TABLE victims AS
SELECT * FROM temp_victims
```

**Metadata Logged**:
- `table_name`: 'victims'
- `rows_loaded`: Number of rows inserted
- `columns_loaded`: Number of columns
- `status`: 'success'

---

## Data Flow

### Input
- **Source**: Google Drive CSV file
- **Format**: CSV with separator '»'
- **Encoding**: ISO-8859-1
- **Location**: `raw_data` folder

### Processing
- All operations happen **in-memory**
- No temporary files created on disk
- Efficient for cloud/containerized environments

### Output
1. **Google Drive**: Clean CSV with '|' separator (UTF-8)
2. **DuckDB**: Structured table for analytics

---

## Key Features

✅ **100% In-Memory Processing**  
- No disk I/O for downloads/uploads
- Faster execution
- Cloud-friendly

✅ **Dual Output**  
- CSV file for sharing/archiving
- Database table for queries/analytics

✅ **Comprehensive Data Cleaning**  
- Handles missing values
- Normalizes strings
- Removes low-quality columns

✅ **Full Observability**  
- Metadata at each step
- Detailed logging
- Easy debugging

✅ **Modular Design**  
- Each step is an independent asset
- Can run individually or as pipeline
- Easy to extend/modify

---

## Configuration Requirements

### Resources Needed
1. **GoogleDriveResource**
   - Credentials: `auth/credentials.json`
   - Token: `auth/token.json`
   - Scopes: `https://www.googleapis.com/auth/drive`

2. **DuckDBResource**
   - Database path: `data/duckdb/prueba.duckdb`

### Google Drive Folder Structure
```
Google Drive Root
├── raw_data/
│   └── 002_victimsmuestra.csv  (or similar)
└── processed_data/
    └── victims_transformed.csv  (created by pipeline)
```

---

## Running the Pipeline

### Run All Assets
```bash
dagster dev
# Then trigger all assets in the UI
```

### Run Individual Assets
```python
# In Dagster UI, you can materialize assets individually:
# 1. extracted_victims_df
# 2. transformed_victims_df
# 3. upload_transformed_victims_csv
# 4. load_victims_to_duckdb
```

### Asset Dependencies
```
extracted_victims_df (independent)
    ↓
transformed_victims_df (depends on extracted_victims_df)
    ↓
    ├── upload_transformed_victims_csv (depends on transformed_victims_df)
    └── load_victims_to_duckdb (depends on transformed_victims_df)
```

---

## Performance Characteristics

### Memory Usage
- Depends on CSV file size
- All processing in RAM
- No disk caching

### Speed
- **Download**: Network-bound
- **Transform**: CPU-bound (pandas operations)
- **Upload**: Network-bound
- **Load**: I/O-bound (DuckDB write)

### Scalability
- Works well for files up to several GB
- For larger files, consider chunking

---

## Error Handling

### Google Drive Errors
- Missing folders: Pipeline fails with clear error message
- No files found: Pipeline fails with clear error message
- Upload failures: Logged and re-raised

### Transformation Errors
- All exceptions logged with context
- Pipeline fails fast to prevent bad data

### Database Errors
- Connection failures: Logged and re-raised
- Table creation failures: Logged and re-raised

---

## Future Enhancements

### Potential Improvements
1. **Partitioning**: Process files by date/batch
2. **Incremental Loads**: Only process new/changed files
3. **Data Validation**: Add schema validation
4. **Notifications**: Send alerts on success/failure
5. **Archiving**: Move processed files to archive folder

### Monitoring
- Add sensors to trigger on new files
- Track processing times
- Monitor data quality metrics

---

## Related Files

- **Assets**: `dagster_pipeline/assets/prueba.py`
- **Google Drive Resource**: `dagster_pipeline/resources/google_drive_resource.py`
- **DuckDB Resource**: `dagster_pipeline/resources/duckdb_connection.py`
- **Definitions**: `dagster_pipeline/definitions.py`

---

**Last Updated**: October 17, 2025  
**Pipeline Version**: 2.0 (Google Drive Integration)
