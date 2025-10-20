# PostgreSQL and MongoDB Loading Assets

## Overview

The pipeline now includes assets to load transformed CSV data into PostgreSQL and MongoDB databases, in addition to the existing Google Drive and DuckDB destinations.

## New Loading Assets

### 1. `load_csv_files_to_postgresql`

Loads all transformed CSV files into PostgreSQL tables.

**Features**:
- Creates or replaces tables based on file names
- Automatically sanitizes table names
- Verifies row counts after loading
- Handles errors gracefully (continues with other files if one fails)

**Example Table Names**:
- `002_victimsmuestra_transformed.csv` → `tbl_002_victimsmuestra_transformed`
- `sales_data_transformed.csv` → `sales_data_transformed`

### 2. `load_csv_files_to_mongodb`

Loads all transformed CSV files into MongoDB collections.

**Features**:
- Creates or replaces collections based on file names
- Automatically sanitizes collection names
- Converts DataFrames to MongoDB documents
- Handles errors gracefully (continues with other files if one fails)

**Example Collection Names**:
- `002_victimsmuestra_transformed.csv` → `col_002_victimsmuestra_transformed`
- `sales_data_transformed.csv` → `sales_data_transformed`

## Data Flow

```
Google Drive (raw_data)
         ↓
   [Extract Asset]
         ↓
  [Transform Asset]
         ↓
    ┌────┴────┬──────────┬──────────┬────────┐
    ↓         ↓          ↓          ↓        ↓
DuckDB   PostgreSQL  MongoDB  Google Drive  (future)
                                (processed_data)
```

## Configuration

### Environment Variables

All database connection settings are configured via environment variables in `.env`:

```bash
# PostgreSQL Configuration
POSTGRES_HOST=postgres          # Docker service name
POSTGRES_PORT=5432
POSTGRES_DB=dagster_pipeline
POSTGRES_USER=juan-wills
POSTGRES_PASSWORD=juan1234

# MongoDB Configuration
MONGO_HOST=mongodb              # Docker service name
MONGO_PORT=27017
MONGO_DB=app_mongo_db
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=juan1234
MONGO_AUTH_SOURCE=admin
```

### Resource Configuration

Resources are configured in `dagster_pipeline/definitions.py`:

```python
defs = Definitions(
    assets=all_assets,
    resources={
        "google_drive": GoogleDriveResource(...),
        "duckdb": database_resource,
        "postgresql": PostgreSQLResource(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "dagster_pipeline"),
            user=os.getenv("POSTGRES_USER", "juan-wills"),
            password=os.getenv("POSTGRES_PASSWORD", "juan1234")
        ),
        "mongodb": MongoDBResource(
            host=os.getenv("MONGO_HOST", "mongodb"),
            port=int(os.getenv("MONGO_PORT", "27017")),
            database=os.getenv("MONGO_DB", "app_mongo_db"),
            username=os.getenv("MONGO_ROOT_USER", "admin"),
            password=os.getenv("MONGO_ROOT_PASSWORD", "juan1234"),
            auth_source=os.getenv("MONGO_AUTH_SOURCE", "admin")
        ),
    },
)
```

## Usage

### Running in Dagster UI

1. **Start all services**:
   ```bash
   docker-compose up -d
   ```

2. **Access Dagster UI**:
   Navigate to http://localhost:3000

3. **Materialize Assets**:
   - Go to Assets view
   - Select the assets you want to run:
     - `extracted_csv_files` (extraction)
     - `transformed_csv_files` (transformation)
     - `load_csv_files_to_postgresql` (load to PostgreSQL)
     - `load_csv_files_to_mongodb` (load to MongoDB)
     - `upload_transformed_csv_files` (upload to Google Drive)
     - `load_csv_files_to_duckdb` (load to DuckDB)
   - Click "Materialize selected"

### Asset Dependencies

All loading assets depend on `transformed_csv_files`:

```
extracted_csv_files
         ↓
transformed_csv_files
         ↓
         ├─→ upload_transformed_csv_files (Google Drive)
         ├─→ load_csv_files_to_duckdb (DuckDB)
         ├─→ load_csv_files_to_postgresql (PostgreSQL) [NEW]
         └─→ load_csv_files_to_mongodb (MongoDB) [NEW]
```

## Verifying Data

### PostgreSQL

**Connect to PostgreSQL**:
```bash
docker exec -it postgres psql -U juan-wills -d dagster_pipeline
```

**List tables**:
```sql
\dt
```

**Query data**:
```sql
SELECT * FROM tbl_002_victimsmuestra_transformed LIMIT 10;
SELECT COUNT(*) FROM tbl_002_victimsmuestra_transformed;
```

**Exit**:
```sql
\q
```

### MongoDB

**Connect to MongoDB**:
```bash
docker exec -it mongodb mongosh -u admin -p juan1234 --authenticationDatabase admin
```

**Switch to database**:
```javascript
use app_mongo_db
```

**List collections**:
```javascript
show collections
```

**Query data**:
```javascript
db.col_002_victimsmuestra_transformed.find().limit(5).pretty()
db.col_002_victimsmuestra_transformed.countDocuments()
```

**Exit**:
```javascript
exit
```

## Asset Metadata

Each loading asset provides metadata about the operation:

### PostgreSQL Asset Metadata
- `tables_created`: Number of tables successfully created
- `table_names`: List of table names
- `total_rows_loaded`: Total number of rows across all tables
- `status`: Operation status

### MongoDB Asset Metadata
- `collections_created`: Number of collections successfully created
- `collection_names`: List of collection names
- `total_documents_loaded`: Total number of documents across all collections
- `status`: Operation status

## Error Handling

Both assets handle errors gracefully:

- **Individual file failures**: If one file fails to load, the asset continues processing other files
- **Detailed logging**: Each step is logged with success (✓) or error (✗) indicators
- **Summary reporting**: Final metadata shows how many items were successfully loaded

Example log output:
```
Loading 002_victimsmuestra_transformed.csv into PostgreSQL table 'tbl_002_victimsmuestra_transformed'...
  ✓ Table 'tbl_002_victimsmuestra_transformed' created with 1500 rows
Loading sales_data_transformed.csv into PostgreSQL table 'sales_data_transformed'...
  ✓ Table 'sales_data_transformed' created with 3200 rows
Successfully loaded 2 table(s) into PostgreSQL
```

## Querying Across Databases

You can now query the same data from different databases:

### PostgreSQL (Relational)
```sql
-- Complex joins and aggregations
SELECT column1, COUNT(*) as count
FROM tbl_002_victimsmuestra_transformed
GROUP BY column1
ORDER BY count DESC;
```

### MongoDB (Document-oriented)
```javascript
// Flexible queries and aggregations
db.col_002_victimsmuestra_transformed.aggregate([
  { $group: { _id: "$column1", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])
```

### DuckDB (Analytical)
```sql
-- Fast analytical queries
SELECT column1, COUNT(*) as count
FROM tbl_002_victimsmuestra_transformed
GROUP BY column1
ORDER BY count DESC;
```

## Performance Considerations

### PostgreSQL
- Best for: ACID transactions, complex joins, relational data
- Performance: Good for < 1M rows per table
- Indexing: Create indexes on frequently queried columns

### MongoDB
- Best for: Flexible schemas, document-oriented data, horizontal scaling
- Performance: Excellent for large datasets with flexible structure
- Indexing: Create indexes on frequently queried fields

### DuckDB
- Best for: Analytical queries, data science workflows, fast aggregations
- Performance: Excellent for analytical queries on large datasets
- In-memory: Very fast for local analysis

## Troubleshooting

### Connection Errors

**PostgreSQL Connection Failed**:
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Verify connection from inside container
docker exec -it postgres psql -U juan-wills -d dagster_pipeline -c "SELECT 1;"
```

**MongoDB Connection Failed**:
```bash
# Check if MongoDB is running
docker-compose ps mongodb

# Check logs
docker-compose logs mongodb

# Verify connection from inside container
docker exec -it mongodb mongosh -u admin -p juan1234 --authenticationDatabase admin --eval "db.adminCommand('ping')"
```

### Table/Collection Already Exists

Both assets use `replace=True` / `if_exists='replace'` by default, so they will:
- Drop existing tables/collections
- Recreate them with new data

### Data Type Issues

If you encounter data type errors:
1. Check the transformation asset - it handles type conversion
2. Verify the data in `transformed_csv_files` asset
3. Check asset logs for specific error messages

## Next Steps

1. ✅ Run the pipeline: `docker-compose up -d`
2. ✅ Materialize assets in Dagster UI
3. ✅ Verify data in PostgreSQL
4. ✅ Verify data in MongoDB
5. 🔄 Create queries or reports using the loaded data
6. 🔄 Set up schedules or sensors for automatic runs

## Additional Resources

- [PostgreSQL Resource Documentation](./DATABASE_SERVICES.md)
- [MongoDB Resource Documentation](./DATABASE_SERVICES.md)
- [Asset Organization Guide](./ASSET_ORGANIZATION.md)
- [Database Quick Start](./DATABASE_QUICKSTART.md)

---

**Created**: October 20, 2025  
**Version**: 1.0.0  
**Status**: Active
