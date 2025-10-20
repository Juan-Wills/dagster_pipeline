# Dagster Pipeline - Documentation

**Version**: 3.0  
**Last Updated**: October 20, 2025  
**Status**: Production Ready ✅

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Asset Organization](#asset-organization)
5. [Database Services](#database-services)
6. [Pipeline Workflows](#pipeline-workflows)
7. [Resources](#resources)
8. [Sensors & Automation](#sensors--automation)
9. [Configuration](#configuration)
10. [Running the Pipeline](#running-the-pipeline)
11. [Troubleshooting](#troubleshooting)
12. [Best Practices](#best-practices)
13. [Future Enhancements](#future-enhancements)

---

## Overview

This Dagster pipeline provides a complete ETL (Extract, Transform, Load) solution for processing CSV files from Google Drive and loading them into multiple database systems.

### Key Features

✅ **Multi-Source Data Extraction**
- Google Drive CSV file **downloads**
- Support for multiple encodings
- Chunked reading for large files (100,000 rows per chunk)

✅ **Comprehensive Data Transformation**
- Column normalization (UPPERCASE)
- Missing value handling (strings → 'NA', numbers → 0)
- Data quality checks (remove high-missing/constant columns)
- String cleaning and standardization
- Duplicate detection and removal

✅ **Multi-Destination Loading**
- Google Drive (processed_data folder)
- DuckDB (analytical queries)
- PostgreSQL (relational data)
- MongoDB (document storage)

✅ **100% In-Memory Processing**
- No temporary files on disk
- Cloud-friendly architecture
- Efficient memory usage

✅ **Automated Monitoring**
- Sensors for new file detection
- Comprehensive logging
- Detailed metadata tracking

---

## Quick Start

### Prerequisites

- Python 3.13+
- Docker & Docker Compose
- Google Drive API credentials

### Installation

```bash
# Clone the repository
cd /home/juan-wills/Documents/dagster_pipeline

# Install dependencies
uv sync --all-groups --no-dev

# Or install groups separately
uv sync --group databases google-api dagster
```

### Start Services

```bash
# Start all Docker services
docker-compose up -d --build

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Access Dagster UI

```bash
# Dagster UI will be available at:
http://localhost:3000
```

### Run Your First Pipeline

1. **Enable the Sensor** (Optional - for automatic processing):
   - Go to Dagster UI → Automation → Sensors
   - Enable `google_drive_new_file_sensor`

2. **Upload Test Files**:
   - Upload CSV files to Google Drive `raw_data` folder

3. **Materialize Assets**:
   - Go to Assets view
   - Select assets to run
   - Click "Materialize selected"

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   DAGSTER PIPELINE ARCHITECTURE             │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  Google Drive    │
│  raw_data folder │
└────────┬─────────┘
         │
         │ [Sensor monitors every 60s]
         │
         ↓
┌──────────────────────────────┐
│  EXTRACTION LAYER            │
│  - extracted_csv_files       │
│  - Download to memory        │
│  - Parse with flexible sep   │
└────────┬─────────────────────┘
         │
         ↓
┌──────────────────────────────┐
│  TRANSFORMATION LAYER        │
│  - transformed_csv_files     │
│  - Clean & normalize         │
│  - Quality checks            │
└────────┬─────────────────────┘
         │
         ├──────────┬──────────┬──────────┬──────────┐
         ↓          ↓          ↓          ↓          ↓
┌───────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐
│  Google   │ │  DuckDB  │ │PostgreSQL│ │ MongoDB│ │ Future │
│   Drive   │ │  Tables  │ │  Tables  │ │ Colls  │ │Targets │
│(processed)│ │          │ │          │ │        │ │        │
└───────────┘ └──────────┘ └──────────┘ └────────┘ └────────┘
```

### Docker Services

The pipeline runs in a Docker environment with the following services:

1. **dagster-webserver**: Web UI for Dagster (port 3000)
2. **dagster-daemon**: Background process for sensors/schedules
3. **codespace**: Development container with pipeline code
4. **postgres**: PostgreSQL for Dagster metadata and app data (port 5432)
6. **mongodb**: MongoDB for document storage (port 27017)

---

## Asset Organization

Assets are organized into three functional layers following the ETL pattern:

### 1. Extraction Assets (`extraction.py`)

**Purpose**: Load and extract data from external sources

**Assets**:
- `extracted_csv_files`: Downloads CSV files from Google Drive

**Responsibilities**:
- Connect to Google Drive
- Download raw data files
- Parse files with multiple encoding/separator attempts
- Handle chunked reading (100,000 rows per chunk)
- Initial data validation
- Return raw DataFrames with metadata

**Location**: `dagster_pipeline/assets/extraction.py`

### 2. Transformation Assets (`transformation.py`)

**Purpose**: Clean, transform, and prepare data

**Assets**:
- `transformed_csv_files`: Transforms and cleans all extracted CSV files

**Transformations Applied**:
1. Column name normalization (UPPERCASE)
2. Remove columns with >90% missing values
3. Remove constant columns (nunique <= 1)
4. String cleaning:
   - Strip whitespace
   - Collapse multiple spaces
   - Convert to UPPERCASE
   - Replace null-like values with 'NA'
5. Missing value handling:
   - String columns → 'NA'
   - Numeric columns → 0
6. Remove empty rows
7. Remove duplicate columns

**Location**: `dagster_pipeline/assets/transformation.py`

### 3. Loading Assets (`loading.py`)

**Purpose**: Persist data to destination systems

**Assets**:
- `upload_transformed_csv_files`: Uploads to Google Drive
- `load_csv_files_to_duckdb`: Loads into DuckDB tables
- `load_csv_files_to_postgresql`: Loads into PostgreSQL tables
- `load_csv_files_to_mongodb`: Loads into MongoDB collections

**Responsibilities**:
- Write data to multiple destinations
- Handle table/collection creation and replacement
- Verify successful data loading
- Generate metadata about loaded data

**Location**: `dagster_pipeline/assets/loading.py`

### Data Flow

```
extracted_csv_files (extraction.py)
         ↓
transformed_csv_files (transformation.py)
         ↓
         ├─→ upload_transformed_csv_files (loading.py)
         ├─→ load_csv_files_to_duckdb (loading.py)
         ├─→ load_csv_files_to_postgresql (loading.py)
         └─→ load_csv_files_to_mongodb (loading.py)
```

---

## Database Services

### PostgreSQL (Dagster Internal)

**Purpose**: Stores application data from the pipeline and Dagster metadata (runs, schedules, sensors)

**Connection Details**:
- Host: `postgres` (Docker) / `localhost` (host)
- Port: `5432`
- Database: `dagster_pipeline`
- Username: `juan-wills`
- Password: `juan1234`

**Connection String**:

```
postgresql://juan-wills:juan1234@localhost:5432/dagster_pipeline
```

**CLI Access**:

```bash
# From host
docker exec -it postgres psql -U juan-wills -d dagster_pipeline

# List tables
\dt

# Query data
SELECT * FROM file_name LIMIT 10;

# Exit
\q
```

### MongoDB

**Purpose**: Document-oriented storage for flexible data

**Connection Details**:
- Host: `mongodb` (Docker) / `localhost` (host)
- Port: `27017`
- Database: `dagster_pipeline`
- Root Username: `juan-wills`
- Root Password: `juan1234`
- Auth Source: `admin`

**Connection String**:
```
mongodb://juan-wills:juan1234@mongodb:27017/dagster_pipeline?authSource=admin
```

**CLI Access**:
```bash
# From host
docker exec -it mongodb mongosh -u juan-wills -p juan1234 --authenticationDatabase admin

# Switch to database
use dagster_pipeline

# List collections
show collections

# Query data
db.collection_name.find().limit(5).pretty()

# Exit
exit
```

### DuckDB

**Purpose**: Fast analytical queries on local data

**Connection Details**:
- Database file: `data/duckdb/prueba.duckdb`

**Usage**:
```python
from dagster_pipeline.resources.duckdb_connection import DuckDBResource

duckdb = DuckDBResource(database_path="data/duckdb/prueba.duckdb")

with duckdb.get_connection() as conn:
    result = conn.execute("SELECT * FROM table_name LIMIT 10").fetchall()
```

### Data Persistence

All database data is persisted in Docker volumes:
- `postgres-data`: Dagster PostgreSQL metadata
- `postgresql-data`: Application PostgreSQL data
- `mongodb-data`: MongoDB data files
- `mongodb-config`: MongoDB configuration files

---

## Pipeline Workflows

### Multi-File CSV Processing Pipeline

This is the main production pipeline that processes ANY CSV files from Google Drive.

**Input**: Multiple CSV files in Google Drive `raw_data/` folder  
**Output**: Cleaned data in 4 destinations (Google Drive, DuckDB, PostgreSQL, MongoDB)

**Key Methods**:
- `find_folder_by_name(folder_name)`: Find folder by name
- `list_files_in_folder(folder_id, mime_type)`: List files in folder
- `download_file(file_id)`: Download file to memory
- `upload_file_from_memory(content, file_name, folder_id)`: Upload from BytesIO
- `create_folder_if_not_exists(folder_name)`: Create folder if needed
- `find_file_in_folder(file_name, folder_id)`: Find file by name
- `delete_file(file_id)`: Delete file

### **Process Flow**:


**Step 1: Extract ALL CSV files from Google Drive**
-  Download to memory (BytesIO)
- Parse with sep='»', encoding='ISO-8859-1'
- Output: List[Dict] with DataFrames and metadata

**Step 2: Transform ALL DataFrames**
-  Normalize columns to UPPERCASE
- Remove high-missing/constant columns
- Clean strings (trim, normalize, uppercase)
- Fill missing values (NA for strings, 0 for numbers)
- Output: List[Dict] with transformed DataFrames

**Step 3a: Upload to Google Drive processed_data/**
-  Convert to CSV with sep='|', encoding='utf-8'
- Upload from memory (BytesIO)
- Replace existing files automatically
- Output: List of uploaded file names

**Step 3b: Load to DuckDB**
-  Create or replace tables
- Table names from file names (sanitized)
- Verify row/column counts
- Output: List of table metadata

**Step 3c: Load to PostgreSQL**
-  Create or replace tables
- Table names from file names (sanitized)
- Verify row counts
- Output: List of table metadata

**Step 3d: Load to MongoDB**
-  Create or replace collections
- Collection names from file names (sanitized)
- Convert DataFrames to documents
- Output: List of collection metadata


**Location**: `dagster_pipeline/resources/google_drive_resource.py`

### DuckDBResource

**Purpose**: Provides DuckDB database connections

**Configuration**:
```python
DuckDBResource(
    database_path="data/duckdb/prueba.duckdb"
)
```

**Key Methods**:
- `get_connection()`: Context manager for database connection

**Location**: `dagster_pipeline/resources/duckdb_connection.py`

### PostgreSQLResource

**Purpose**: Provides PostgreSQL database operations

**Configuration**:
```python
PostgreSQLResource(
    host="localhost",  # or "postgresql" in Docker
    port=5433,
    database="dagster_pipeline",
    user="juan-wills",
    password="juan1234"
)
```

**Key Methods**:
- `get_connection()`: Context manager for database connection
- `execute_query(query, params)`: Execute SQL query
- `create_table_from_dataframe(df, table_name, if_exists)`: Create table from DataFrame

**Location**: `dagster_pipeline/resources/postgresql_resource.py`

### MongoDBResource

**Purpose**: Provides MongoDB database operations

**Configuration**:
```python
MongoDBResource(
    host="localhost",  # or "mongodb" in Docker
    port=27017,
    database="dagster_pipeline",
    username="juan-wills",
    password="juan1234",
    auth_source="admin"
)
```

**Key Methods**:
- `get_client()`: Get MongoDB client
- `get_database()`: Context manager for database connection
- `get_collection(collection_name)`: Context manager for collection
- `insert_dataframe(collection_name, df, replace)`: Insert DataFrame as documents
- `find_many(collection_name, filter, limit)`: Query documents
- `collection_exists(collection_name)`: Check if collection exists
- `drop_collection(collection_name)`: Delete collection

**Location**: `dagster_pipeline/resources/mongodb_resource.py`

---

## Sensors & Automation

### google_drive_new_file_sensor

**Purpose**: Monitors Google Drive `raw_data/` folder for new CSV files

**Configuration**:
```python
@sensor(
    name="google_drive_new_file_sensor",
    minimum_interval_seconds=60,  # Check every 60 seconds
    ...
)
```

**How It Works**:
1. Checks `raw_data/` folder every 60 seconds
2. Lists all CSV files (mimeType='text/csv')
3. Compares with cursor (previously seen file IDs)
4. Detects new files: `new_files = current_files - seen_files`
5. Triggers `process_drive_files` asset when new files detected
6. Updates cursor with new file IDs

**State Management**:
```json
{
  "file_ids": ["1abc", "2def", "3ghi"],
  "last_check": "2025-10-20T10:30:00"
}
```

**Enabling the Sensor**:
1. Open Dagster UI → Automation → Sensors
2. Find `google_drive_new_file_sensor`
3. Toggle to enable
4. Sensor will start checking every 60 seconds

**Testing**:
1. Upload a CSV file to Google Drive `raw_data/` folder
2. Wait up to 60 seconds
3. Check Dagster UI → Runs tab for triggered execution

**Location**: `dagster_pipeline/sensors/sensors.py`

---

## Configuration

### Environment Variables

All configuration is stored in `.env` file:

```bash
# Dagster PostgreSQL (Internal)
DAGSTER_PG_HOST=postgres
DAGSTER_PG_PORT=5432
DAGSTER_HOME=/dagster_pipeline/config/
DAGSTER_PG_USER= ...
DAGSTER_PG_PASSWORD= ...
DAGSTER_PG_DB= ...

# Application PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB= ...
POSTGRES_USER= ...
POSTGRES_PASSWORD= ...

# MongoDB
MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_AUTH_SOURCE=admin
MONGO_ROOT_USER= ...
MONGO_ROOT_PASSWORD= ...
MONGO_DB= ...

# Dagster Docker
DAGSTER_CURRENT_IMAGE=dagster_pipeline-codespace
```

⚠️ **Security Note**: Change passwords for production use!

### Google Drive Setup

1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project

2. **Enable Google Drive API**:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click "Enable"

3. **Create OAuth Credentials**:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Choose "Desktop app"
   - Download JSON file

4. **Save Credentials**:
   - Save downloaded file as `auth/credentials.json`
   - First run will prompt for authentication
   - Token will be saved to `auth/token.json`

5. **Create Folders in Google Drive**:
   - Create `raw_data` folder (for source files)
   - `processed_data` folder will be created automatically

### Definitions

Main pipeline configuration in `dagster_pipeline/definitions.py`:

```python
from dagster import Definitions
from dagster_pipeline.resources import (
    GoogleDriveResource,
    PostgreSQLResource,
    MongoDBResource,
    DuckDBResource
)
from dagster_pipeline.assets import all_assets
from dagster_pipeline.sensors import all_sensors

defs = Definitions(
    assets=all_assets,
    resources={
        "google_drive": GoogleDriveResource(...),
        "duckdb": DuckDBResource(...),
        "postgresql": PostgreSQLResource(...),
        "mongodb": MongoDBResource(...),
    },
    sensors=all_sensors,
)
```

---

## Running the Pipeline

### Starting Services

```bash
# Start all services
docker-compose up -d --build

# Check service status
docker-compose ps

# View logs
docker-compose logs -f dagster-webserver
docker-compose logs -f dagster-daemon
```

### Accessing Dagster UI

```bash
# Dagster UI available at:
http://localhost:3000

# From UI you can:
# - View assets and their lineage
# - Materialize assets
# - Monitor runs
# - Enable/disable sensors
# - View logs and metadata
```

### Materializing Assets

**Option 1: Run All Assets Together**
1. Go to Assets view
2. Select all assets:
   - `extracted_csv_files`
   - `transformed_csv_files`
   - `upload_transformed_csv_files`
   - `load_csv_files_to_duckdb`
   - `load_csv_files_to_postgresql`
   - `load_csv_files_to_mongodb`
3. Click "Materialize selected"

**Option 2: Run Step by Step**
1. Materialize: `extracted_csv_files`
2. Materialize: `transformed_csv_files`
3. Materialize loading assets (any/all):
   - `upload_transformed_csv_files`
   - `load_csv_files_to_duckdb`
   - `load_csv_files_to_postgresql`
   - `load_csv_files_to_mongodb`

**Option 3: Use Sensor (Automatic)**
1. Enable `google_drive_new_file_sensor`
2. Upload files to Google Drive `raw_data/`
3. Wait for sensor to trigger (60 seconds)
4. Pipeline runs automatically

### Monitoring Execution

**View Run Details**:
- Go to Runs tab
- Click on run to see:
  - Asset execution order
  - Logs for each asset
  - Metadata (row counts, file names, etc.)
  - Execution time
  - Success/failure status

**View Asset Lineage**:
- Go to Assets view
- Click on any asset
- View "Upstream" and "Downstream" assets
- See dependency graph

**Check Metadata**:
- Each asset provides metadata:
  - Files processed
  - Rows/columns
  - Tables/collections created
  - Upload status

---

## Troubleshooting

### Common Issues

#### 1. FileNotFoundError when running loading assets

**Error**:
```
FileNotFoundError: [Errno 2] No such file or directory: 
'/dagster_pipeline/.dagster/storage/storage/transformed_csv_files'
```

**Cause**: Trying to run a loading asset without first materializing `transformed_csv_files`

**Solution**: 
- Always materialize upstream assets first
- OR materialize all assets together

#### 2. Google Drive Authentication Failed

**Error**: `Authentication failed` or `Invalid credentials`

**Solution**:
```bash
# Delete old token
rm auth/token.json

# Restart Dagster
docker-compose restart dagster-webserver

# Run pipeline again - it will prompt for authentication
```

#### 3. Database Connection Refused

**Error**: `Connection refused` for PostgreSQL or MongoDB

**Solution**:
```bash
# Check services are running
docker-compose ps

# Check logs
docker-compose logs postgres
docker-compose logs mongodb

# Restart services
docker-compose restart postgres mongodb

# Verify connection
docker exec -it postgres psql -U juan-wills -d dagster_pipeline -c "SELECT 1;"
docker exec -it mongodb mongosh -u juan-wills -p juan1234 --authenticationDatabase admin --eval "db.adminCommand('ping')"
```

#### 4. Port Already in Use

**Error**: `Bind for 0.0.0.0:5432 failed: port is already allocated`

**Solution**:
```bash
# Check what's using the port
sudo netstat -tulpn | grep :5432

# Stop the conflicting service
# OR change port in docker-compose.yml
ports:
  - "5434:5432"  # Changed from 5432:5432
```

#### 5. Sensor Not Triggering

**Cause**: Sensor is disabled or folder doesn't exist

**Solution**:
1. Check sensor is enabled in Dagster UI
2. Verify `raw_data` folder exists in Google Drive
3. Check sensor logs in Dagster UI
4. Verify CSV files are in `raw_data` (not subfolder)

#### 6. Data Not Appearing in Database

**Solution**:
```bash
# PostgreSQL - Check tables exist
docker exec -it postgres psql -U juan-wills -d dagster_pipeline -c "\dt"

# MongoDB - Check collections exist
docker exec -it mongodb mongosh dagster_pipeline -u juan-wills -p juan1234 --authenticationDatabase admin --eval "show collections"

# Check Dagster logs for errors
docker-compose logs dagster-webserver | grep -i error
```

### Getting Help

**Check Logs**:
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs dagster-webserver
docker-compose logs dagster-daemon

# Follow logs in real-time
docker-compose logs -f
```

**Reset Everything** (⚠️ Deletes all data):
```bash
docker-compose down -v
docker-compose up -d --build
```

**Check Service Health**:
```bash
# Check all containers
docker ps

# Check specific container
docker inspect postgres | grep Status
docker inspect mongodb | grep Status
```

---

## Best Practices

### 1. Asset Materialization

**DO**:
- Materialize upstream assets before downstream ones
- OR materialize entire asset graph together
- Check asset lineage before running

**DON'T**:
- Don't run loading assets without transformation assets
- Don't skip extraction or transformation steps

### 2. Data Quality

**DO**:
- Review transformation logs for data quality issues
- Check metadata for row/column counts
- Validate data in destination databases

**DON'T**:
- Don't skip transformation step
- Don't ignore warnings in logs

### 3. Security

**DO**:
- Change default passwords in production
- Use environment variables for secrets
- Keep `.env` file out of version control
- Add `.env` to `.gitignore`

**DON'T**:
- Don't commit credentials to Git
- Don't use default passwords in production
- Don't expose database ports publicly

### 4. Monitoring

**DO**:
- Monitor sensor execution
- Check run history regularly
- Review asset metadata
- Set up alerts for failures

**DON'T**:
- Don't ignore failed runs
- Don't let errors accumulate

### 5. Performance

**DO**:
- Use chunked reading for large files
- Monitor memory usage
- Consider partitioning for very large datasets

**DON'T**:
- Don't load entire large files into memory at once
- Don't run too many assets in parallel if memory-constrained

---

## Future Enhancements

### Planned Features

#### Data Processing
- [ ] Incremental processing (only new/changed files)
- [ ] File filtering by pattern (include/exclude)
- [ ] Custom transformation rules per file type
- [ ] Schema validation before loading
- [ ] Data lineage tracking

#### Automation
- [ ] Email/Slack notifications on completion
- [ ] Automatic retry on transient failures
- [ ] Scheduled runs (daily, weekly, etc.)
- [ ] Multiple sensors for different folders
- [ ] File archiving after processing

#### Databases
- [ ] Additional database connectors (Snowflake, Redshift, BigQuery)
- [ ] Support for database migrations
- [ ] Incremental table updates
- [ ] Data versioning

#### Monitoring
- [ ] Data quality metrics dashboard
- [ ] Performance monitoring
- [ ] Alert on data anomalies
- [ ] Cost tracking

#### Testing
- [ ] Unit tests for assets
- [ ] Integration tests for full pipeline
- [ ] Data validation tests
- [ ] Performance benchmarks

---

## File Structure

```
dagster_pipeline/
├── auth/
│   ├── credentials.json         # Google Drive API credentials
│   └── token.json              # OAuth token (auto-generated)
│
├── config/
│   ├── dagster.yaml            # Dagster configuration
│   └── workspace.yaml          # Workspace configuration
│
├── dagster_pipeline/
│   ├── __init__.py
│   ├── definitions.py          # Main definitions (assets, resources, sensors)
│   │
│   ├── assets/
│   │   ├── __init__.py
│   │   ├── extraction.py       # Extraction assets
│   │   ├── transformation.py   # Transformation assets
│   │   └── loading.py          # Loading assets
│   │
│   ├── resources/
│   │   ├── __init__.py
│   │   ├── google_drive_resource.py
│   │   ├── duckdb_connection.py
│   │   ├── postgresql_resource.py
│   │   └── mongodb_resource.py
│   │
│   ├── sensors/
│   │   ├── __init__.py
│   │   └── sensors.py          # Sensor definitions
│   │
│   ├── schedules/
│   │   ├── __init__.py
│   │   └── schedules.py        # Schedule definitions
│   │
│   └── jobs/
│       ├── __init__.py
│       └── __pycache__/
│
├── data/
│   ├── duckdb/                 # DuckDB database files
│   ├── processed/              # Processed data (local)
│   ├── raw/                    # Raw data (local)
│   └── temp/                   # Temporary files
│
├── docker/
│   ├── codespace.Dockerfile
│   └── dagster_services.Dockerfile
│
├── docs/                       # Documentation (this file and others)
│   └── COMPLETE_DOCUMENTATION.md
│
├── tests/                      # Test files
│   ├── __init__.py
│   ├── conftest.py
│   └── test_database_connections.py
│
├── .env                        # Environment variables (not in Git)
├── .gitignore
├── docker-compose.yml          # Docker services configuration
├── pyproject.toml             # Python dependencies
├── README.md
└── setup.py
```

---

## Glossary

**Asset**: A software-defined data artifact (table, file, ML model, etc.)

**Asset Materialization**: The process of computing/creating an asset

**Resource**: A reusable connection or service (database, API, etc.)

**Sensor**: An automation that monitors for events and triggers runs

**Schedule**: Time-based automation that triggers runs on a schedule

**Run**: A single execution of an asset or job

**Cursor**: State tracking for sensors (what's been seen/processed)

**IOManager**: Handles serialization/deserialization of asset values

**Op**: A unit of computation (function that does work)

**Job**: A collection of ops to execute together

**Partition**: A slice of data (by date, category, etc.)

---

## Version History

### Version 3.0 (Current) - October 20, 2025
- ✅ Multi-file CSV processing
- ✅ PostgreSQL and MongoDB loading
- ✅ Duplicate file handling
- ✅ Asset reorganization (extraction/transformation/loading)
- ✅ Complete Docker setup
- ✅ Comprehensive documentation

### Version 2.0 - October 17, 2025
- ✅ Google Drive integration
- ✅ In-memory processing
- ✅ DuckDB loading
- ✅ Sensor-based automation

### Version 1.0 - October 16, 2025
- ✅ Initial pipeline structure
- ✅ Basic ETL assets
- ✅ Local file processing

---

## Support & Contact

For issues, questions, or contributions:

1. Check this documentation
2. Review troubleshooting section
3. Check Dagster logs
4. Consult [Dagster Documentation](https://docs.dagster.io/)

---
*For more detailed information lead to the specific documentation in `\docs`*