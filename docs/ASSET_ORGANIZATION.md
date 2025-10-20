# Asset Organization Guide

## Overview

The Dagster assets have been reorganized into three categories based on their function in the ETL pipeline. This structure makes the codebase more maintainable and follows the separation of concerns principle.

## Asset Categories

### 1. Extraction (`extraction.py`)

**Purpose**: Loading and extracting data from external sources

**Assets**:
- `extracted_csv_files` - Downloads CSV files from Google Drive and performs initial parsing

**Responsibilities**:
- Connect to external data sources (Google Drive)
- Download/fetch raw data
- Parse files with multiple encoding/separator attempts
- Handle chunked reading (100,000 rows per chunk)
- Initial data validation
- Return raw DataFrames with metadata

**Location**: `dagster_pipeline/assets/extraction.py`

### 2. Transformation (`transformation.py`)

**Purpose**: Cleaning, transforming, and preparing data

**Assets**:
- `transformed_csv_files` - Transforms and cleans all extracted CSV files

**Responsibilities**:
- Column name normalization
- Remove columns with excessive missing values
- Data type identification and conversion
- String cleaning and standardization
- Numeric value handling
- Remove empty rows and constant columns
- Remove duplicate columns
- Data validation and quality checks

**Location**: `dagster_pipeline/assets/transformation.py`

### 3. Loading (`loading.py`)

**Purpose**: Persisting data to destination systems

**Assets**:
- `upload_transformed_csv_files` - Uploads transformed data to Google Drive
- `load_csv_files_to_duckdb` - Loads transformed data into DuckDB database

**Responsibilities**:
- Write data to Google Drive (processed_data folder)
- Load data into DuckDB tables
- Handle table creation and replacement
- Manage file uploads and replacements
- Verify successful data loading
- Generate metadata about loaded data

**Location**: `dagster_pipeline/assets/loading.py`

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTRACTION                                │
│                  (extraction.py)                             │
│                                                              │
│  • Google Drive Download                                     │
│  • File Parsing (multiple attempts)                          │
│  • Chunked Reading (100k rows)                               │
│  • Raw DataFrame Creation                                    │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ↓ extracted_csv_files
                       │
┌──────────────────────┴───────────────────────────────────────┐
│                  TRANSFORMATION                              │
│                (transformation.py)                           │
│                                                              │
│  • Column Normalization                                      │
│  • Data Cleaning                                             │
│  • Type Conversion                                           │
│  • Quality Checks                                            │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ↓ transformed_csv_files
                       │
                       ├─────────────────┬─────────────────┐
                       ↓                 ↓                 ↓
┌──────────────────────────────────────────────────────────────┐
│                     LOADING                                  │
│                   (loading.py)                               │
│                                                              │
│  ┌─────────────────────┐    ┌─────────────────────┐        │
│  │  Google Drive       │    │     DuckDB          │        │
│  │  Upload             │    │     Tables          │        │
│  │  (processed_data)   │    │     (local DB)      │        │
│  └─────────────────────┘    └─────────────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

## File Structure

```
dagster_pipeline/assets/
├── __init__.py              # Exports all assets
├── extraction.py            # Category 1: Data extraction
├── transformation.py        # Category 2: Data transformation
├── loading.py              # Category 3: Data loading
├── database_examples.py    # Example database assets
└── google_drive_etl.py     # (DEPRECATED - kept for reference)
```

## Benefits of This Organization

### 1. **Clear Separation of Concerns**
Each file has a single, well-defined purpose:
- Extraction: Get data IN
- Transformation: Clean data
- Loading: Put data OUT

### 2. **Easier Maintenance**
- Locate issues quickly based on pipeline stage
- Modify extraction logic without touching transformation
- Add new loading destinations without affecting other stages

### 3. **Better Scalability**
- Easy to add new extraction sources
- Simple to add new transformation steps
- Straightforward to add new loading destinations

### 4. **Improved Readability**
- Each file is focused and easier to understand
- New developers can grasp the pipeline structure quickly
- Clear naming conventions

### 5. **Testing Isolation**
- Test extraction independently
- Test transformations with mock data
- Test loading with mock databases

## Adding New Assets

### Adding a New Extraction Source

Create a new asset in `extraction.py`:

```python
@dg.asset(
    kinds={"api", "json"},
    description="Extract data from external API"
)
def extracted_api_data(
    context: AssetExecutionContext,
    api_client: APIResource
) -> Output[List[Dict]]:
    # Extraction logic here
    pass
```

### Adding a New Transformation

Create a new asset in `transformation.py`:

```python
@dg.asset(
    kinds={"pandas"},
    description="Custom transformation for specific use case"
)
def custom_transformed_data(
    context: AssetExecutionContext,
    extracted_csv_files: List[Dict]
) -> Output[List[Dict]]:
    # Transformation logic here
    pass
```

### Adding a New Loading Destination

Create a new asset in `loading.py`:

```python
@dg.asset(
    kinds={"postgresql"},
    description="Load data into PostgreSQL",
    deps=["transformed_csv_files"]
)
def load_to_postgresql(
    context: AssetExecutionContext,
    postgresql: PostgreSQLResource,
    transformed_csv_files: List[Dict]
) -> Output[Dict]:
    # Loading logic here
    pass
```

## Import Pattern

All assets are imported through `__init__.py`:

```python
# In your definitions.py or other modules
from dagster_pipeline.assets import (
    extracted_csv_files,      # Extraction
    transformed_csv_files,    # Transformation
    upload_transformed_csv_files,  # Loading
    load_csv_files_to_duckdb       # Loading
)
```

## Migration from Old Structure

The old `google_drive_etl.py` file has been split into three files:
- ❌ `google_drive_etl.py` (deprecated, can be removed)
- ✅ `extraction.py` (new)
- ✅ `transformation.py` (new)
- ✅ `loading.py` (new)

**No changes needed in `definitions.py`** - the imports still work through `__init__.py`.

## Asset Dependencies

```
extracted_csv_files (extraction.py)
         ↓
transformed_csv_files (transformation.py)
         ↓
         ├─→ upload_transformed_csv_files (loading.py)
         └─→ load_csv_files_to_duckdb (loading.py)
```

## Best Practices

1. **Keep extraction pure** - Only fetch and parse data, no transformation
2. **Make transformations idempotent** - Same input = same output
3. **Loading should be atomic** - All or nothing for each destination
4. **Log extensively** - Each stage should log progress and issues
5. **Handle errors gracefully** - Continue processing other files if one fails

## Future Enhancements

Potential additions to each category:

### Extraction
- [ ] Add S3 extraction asset
- [ ] Add database extraction asset
- [ ] Add API extraction asset

### Transformation
- [ ] Add data validation asset
- [ ] Add data enrichment asset
- [ ] Add schema standardization asset

### Loading
- [ ] Add PostgreSQL loading asset
- [ ] Add MongoDB loading asset
- [ ] Add Parquet file export asset

---

**Created**: October 20, 2025  
**Version**: 1.0.0  
**Status**: Active
