# Troubleshooting Asset Materialization Issues

## Problem: FileNotFoundError when running loading assets

### Error Message
```
FileNotFoundError: [Errno 2] No such file or directory: 
'/dagster_pipeline/.dagster/storage/storage/transformed_csv_files'
```

### Root Cause

This error occurs when you try to materialize a loading asset (e.g., `load_csv_files_to_mongodb`) without first materializing its upstream dependency (`transformed_csv_files`) in the current session.

The issue happens because:
1. Loading assets depend on `transformed_csv_files` 
2. `transformed_csv_files` returns a complex data structure: `List[Dict]` with pandas DataFrames
3. When you run only the loading asset, Dagster's IO manager tries to load the data from disk storage
4. The default IO manager has difficulty serializing/deserializing this complex structure

### Solution 1: Materialize Assets in Correct Order (Recommended)

**Always materialize upstream assets first, or materialize all assets together.**

#### Option A: Materialize All Assets Together
In Dagster UI:
1. Go to Assets view
2. Select all assets you want to run:
   - ✅ `extracted_csv_files`
   - ✅ `transformed_csv_files`
   - ✅ `load_csv_files_to_postgresql`
   - ✅ `load_csv_files_to_mongodb`
   - ✅ `load_csv_files_to_duckdb`
   - ✅ `upload_transformed_csv_files`
3. Click "Materialize selected"

#### Option B: Materialize Step by Step
1. First materialize: `extracted_csv_files`
2. Then materialize: `transformed_csv_files`
3. Finally materialize any/all loading assets:
   - `load_csv_files_to_postgresql`
   - `load_csv_files_to_mongodb`
   - `load_csv_files_to_duckdb`
   - `upload_transformed_csv_files`

### Solution 2: Understanding Asset Dependencies

The loading assets now properly declare their dependencies through function parameters:

```python
@dg.asset(
    kinds={"mongodb"},
    description="Loads all transformed CSV files into MongoDB collections"
)
def load_csv_files_to_mongodb(
    context: AssetExecutionContext,
    mongodb: MongoDBResource,
    transformed_csv_files: List[Dict]  # ← This creates the dependency
) -> Output[List[Dict]]:
    ...
```

When `transformed_csv_files` is in the function signature, Dagster knows:
- This asset depends on `transformed_csv_files`
- It needs to either:
  - Load it from the current run if it was just materialized
  - Load it from storage if it was materialized in a previous run

### Solution 3: Using Asset Jobs (Advanced)

You can create a job that materializes assets in the correct order:

```python
from dagster import define_asset_job, AssetSelection

# In your definitions.py
full_pipeline_job = define_asset_job(
    name="full_etl_pipeline",
    selection=AssetSelection.all()
)

database_loading_job = define_asset_job(
    name="database_loading",
    selection=AssetSelection.assets(
        extracted_csv_files,
        transformed_csv_files,
        load_csv_files_to_postgresql,
        load_csv_files_to_mongodb
    )
)
```

Then add to your Definitions:
```python
defs = Definitions(
    assets=all_assets,
    resources={...},
    jobs=[full_pipeline_job, database_loading_job],
    sensors=[...],
)
```

### What Was Fixed

I removed the redundant `deps=["transformed_csv_files"]` declarations from the loading assets. This was causing confusion because:

**Before (problematic)**:
```python
@dg.asset(
    deps=["transformed_csv_files"]  # ← Redundant!
)
def load_csv_files_to_mongodb(
    transformed_csv_files: List[Dict]  # ← Already declares dependency
):
    ...
```

**After (fixed)**:
```python
@dg.asset()
def load_csv_files_to_mongodb(
    transformed_csv_files: List[Dict]  # ← This is enough
):
    ...
```

### Best Practices

1. **Always materialize upstream assets first**
   - Or materialize the entire asset graph together

2. **Check asset lineage**
   - Use the "Global Asset Lineage" view in Dagster UI
   - Understand dependencies before running assets

3. **Use asset groups or jobs**
   - Group related assets together
   - Create jobs for common workflows

4. **Monitor storage**
   - Check `/dagster_pipeline/.dagster/storage/storage/`
   - Ensure disk space is available

### Verifying the Fix

After restarting Dagster:

```bash
# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Check logs
docker-compose logs -f dagster-webserver
```

Then in Dagster UI:
1. Go to Assets
2. Select all assets (or at least `extracted_csv_files`, `transformed_csv_files`, and your loading assets)
3. Click "Materialize selected"
4. Watch the run progress - all assets should execute in order

### Expected Behavior

When you materialize all assets together:

```
1. extracted_csv_files
   Status: Running → Complete ✓
   
2. transformed_csv_files (waits for #1)
   Status: Waiting → Running → Complete ✓
   
3. All loading assets (wait for #2, can run in parallel):
   - load_csv_files_to_postgresql
   - load_csv_files_to_mongodb  
   - load_csv_files_to_duckdb
   - upload_transformed_csv_files
   Status: Waiting → Running → Complete ✓
```

### Additional Tips

**If you still see the error:**

1. **Clear Dagster storage**:
   ```bash
   docker-compose down
   docker volume rm dagster_pipeline_postgres-data
   docker-compose up -d
   ```

2. **Check asset output paths**:
   ```bash
   docker exec -it codespace ls -la /dagster_pipeline/.dagster/storage/storage/
   ```

3. **Verify assets are loaded**:
   - Check Dagster UI → Assets
   - All assets should be visible
   - Check for any errors in the "Definitions" tab

4. **Check logs for other errors**:
   ```bash
   docker-compose logs dagster-webserver | grep -i error
   docker-compose logs dagster-deamon | grep -i error
   ```

---

**Summary**: The fix removes redundant `deps` declarations. Always materialize upstream assets before downstream ones, or materialize the entire asset graph together to avoid storage issues.
