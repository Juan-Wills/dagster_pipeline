"""Loading Assets

This module contains assets responsible for:
- Loading transformed data into destination systems
- Uploading files to storage services (Google Drive)
- Writing to databases (DuckDB, PostgreSQL, MongoDB)
- Data persistence and storage
"""

import io

import dagster as dg
from dagster import AssetExecutionContext, Output, AssetCheckResult, AssetCheckSeverity, asset_check
from dagster_pipeline.resources.duckdb_connection import DuckDBResource
from dagster_pipeline.resources.google_drive_resource import GoogleDriveResource
from dagster_pipeline.resources.postgresql_resource import PostgreSQLResource
from dagster_pipeline.resources.mongodb_resource import MongoDBResource

from typing import List, Dict


@dg.asset(
    kinds={"google_drive", "csv"},
    description="Uploads all transformed CSV files to Google Drive processed_data folder"
)
def upload_transformed_csv_files(
    context: AssetExecutionContext,
    google_drive: GoogleDriveResource,
    transformed_csv_files: List[Dict]
) -> Output[List[Dict]]:
    """
    Step 3a (Load to Google Drive): Uploads all transformed DataFrames to Google Drive.
    Uploads to the processed_data folder in Google Drive.
    Replaces existing files with the same name to avoid duplicates.
    """
    
    if not transformed_csv_files:
        context.log.info("No files to upload")
        return Output(value=[], metadata={
            "files_uploaded": 0,
            "message": "No files to upload"
        })
    
    # Create or find processed_data folder in Google Drive
    processed_folder_id = google_drive.create_folder_if_not_exists("processed_data")
    context.log.info(f"Using 'processed_data' folder (ID: {processed_folder_id})")
    
    uploaded_files = []
    replaced_count = 0
    created_count = 0
    
    for file_data in transformed_csv_files:
        file_name = file_data['output_file_name']
        df = file_data['dataframe']
        
        context.log.info(f"Uploading: {file_name}")
        
        # Convert DataFrame to CSV in memory
        csv_content = io.BytesIO()
        df.to_csv(
            csv_content,
            encoding='utf-8',
            sep='|',
            index=False
        )
        
        # Upload to Google Drive (will replace if exists)
        try:
            uploaded = google_drive.upload_file_from_memory(
                csv_content,
                file_name,
                processed_folder_id,
                replace_if_exists=True  # Replace existing files
            )
            action = uploaded.get('action', 'created')
            
            if action == 'replaced':
                replaced_count += 1
                context.log.info(f"  ✓ Replaced existing file: {uploaded['name']} (ID: {uploaded['id']})")
            else:
                created_count += 1
                context.log.info(f"  ✓ Created new file: {uploaded['name']} (ID: {uploaded['id']})")
            
            uploaded_files.append({
                'file_name': file_name,
                'name': uploaded['name'],
                'id': uploaded['id'],
                'action': action,
                'status': 'success'
            })
        except Exception as e:
            context.log.error(f"  ✗ Error uploading {file_name}: {str(e)}")
            # Track failed uploads
            uploaded_files.append({
                'file_name': file_name,
                'name': file_name,
                'id': None,
                'action': 'failed',
                'status': 'failed',
                'error': str(e)
            })
    
    # Count successful vs failed uploads
    successful_uploads = [f for f in uploaded_files if f.get('status') == 'success']
    failed_uploads = [f for f in uploaded_files if f.get('status') == 'failed']
    
    context.log.info(
        f"Upload completed. {len(successful_uploads)}/{len(uploaded_files)} file(s) uploaded successfully "
        f"({created_count} new, {replaced_count} replaced, {len(failed_uploads)} failed)"
    )
    
    return Output(
        value=uploaded_files,
        metadata={
            "files_uploaded": len(successful_uploads),
            "files_created": created_count,
            "files_replaced": replaced_count,
            "files_failed": len(failed_uploads),
            "file_names": [f['name'] for f in successful_uploads],
            "total_rows": sum(f['row_count'] for f in transformed_csv_files)
        }
    )


@dg.asset(
    kinds={"duckdb"},
    description="Loads all transformed CSV files into DuckDB tables"
)
def load_csv_files_to_duckdb(
    context: AssetExecutionContext,
    duckdb: DuckDBResource,
    transformed_csv_files: List[Dict]
) -> Output[List[Dict]]:
    """
    Step 3b (Load to DuckDB): Loads all transformed DataFrames into DuckDB.
    Creates or replaces tables with sanitized names based on the file names.
    """
    
    if not transformed_csv_files:
        context.log.info("No files to load into DuckDB")
        return Output(value=[], metadata={
            "tables_created": 0,
            "message": "No files to load"
        })
    
    context.log.info(f"Loading {len(transformed_csv_files)} file(s) to DuckDB...")
    
    loaded_tables = []
    
    try:
        with duckdb.get_connection() as conn:
            
            for file_data in transformed_csv_files:
                file_name = file_data['output_file_name']
                df = file_data['dataframe']
                
                # Create table name from file name (sanitize)
                # Remove .csv extension and replace special chars with underscores
                table_name = file_name.rsplit('.', 1)[0].lower()
                table_name = ''.join(c if c.isalnum() else '_' for c in table_name)
                
                # Ensure table name doesn't start with a number (invalid SQL)
                if table_name and table_name[0].isdigit():
                    table_name = f"tbl_{table_name}"
                
                context.log.info(f"Loading {file_name} into table '{table_name}'...")
                
                # Register the DataFrame as a temporary view
                temp_view_name = f"temp_{table_name}"
                conn.register(temp_view_name, df)
                
                # Create or replace the table
                create_query = f"""
                    CREATE OR REPLACE TABLE {table_name} AS
                    SELECT * FROM {temp_view_name}
                """
                conn.execute(create_query)
                context.log.info(f"  Table '{table_name}' created/replaced successfully")
                
                # Verify the load
                row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]  # type: ignore
                
                # Get column count
                column_count = conn.execute(
                    f"SELECT COUNT(*) FROM information_schema.columns WHERE table_name = '{table_name}'"
                ).fetchone()[0]  # type: ignore
                
                context.log.info(f"  Verified: {row_count} rows and {column_count} columns loaded")
                
                loaded_tables.append({
                    "table_name": table_name,
                    "source_file": file_name,
                    "row_count": row_count,
                    "column_count": column_count
                })
            
            context.log.info(f"Successfully loaded {len(loaded_tables)} table(s) into DuckDB")
            
            return Output(
                value=loaded_tables,
                metadata={
                    "tables_created": len(loaded_tables),
                    "table_names": [t['table_name'] for t in loaded_tables],
                    "total_rows_loaded": sum(t['row_count'] for t in loaded_tables),
                    "status": "success"
                }
            )
            
    except Exception as e:
        context.log.error(f"Error loading data into DuckDB: {str(e)}")
        raise


@dg.asset(
    kinds={"postgresql"},
    description="Loads all transformed CSV files into PostgreSQL tables"
)
def load_csv_files_to_postgresql(
    context: AssetExecutionContext,
    postgresql: PostgreSQLResource,
    transformed_csv_files: List[Dict]
) -> Output[List[Dict]]:
    """
    Step 3c (Load to PostgreSQL): Loads all transformed DataFrames into PostgreSQL.
    Creates or replaces tables with sanitized names based on the file names.
    """
    
    if not transformed_csv_files:
        context.log.info("No files to load into PostgreSQL")
        return Output(value=[], metadata={
            "tables_created": 0,
            "message": "No files to load"
        })
    
    context.log.info(f"Loading {len(transformed_csv_files)} file(s) to PostgreSQL...")
    
    loaded_tables = []
    
    try:
        for file_data in transformed_csv_files:
            file_name = file_data['output_file_name']
            df = file_data['dataframe']
            
            # Create table name from file name (sanitize)
            # Remove .csv extension and replace special chars with underscores
            table_name = file_name.rsplit('.', 1)[0].lower()
            table_name = ''.join(c if c.isalnum() else '_' for c in table_name)
            
            # Ensure table name doesn't start with a number (invalid SQL)
            if table_name and table_name[0].isdigit():
                table_name = f"tbl_{table_name}"
            
            context.log.info(f"Loading {file_name} into PostgreSQL table '{table_name}'...")
            
            try:
                # Create table from DataFrame
                postgresql.create_table_from_dataframe(
                    df=df,
                    table_name=table_name,
                    if_exists='replace'
                )
                
                # Verify the load
                query = f"SELECT COUNT(*) FROM {table_name}"
                result = postgresql.execute_query(query)
                row_count = result[0][0] if result else 0
                
                context.log.info(f"  ✓ Table '{table_name}' created with {row_count} rows")
                
                loaded_tables.append({
                    "table_name": table_name,
                    "source_file": file_name,
                    "row_count": row_count,
                    "column_count": len(df.columns)
                })
                
            except Exception as e:
                context.log.error(f"  ✗ Error loading table '{table_name}': {str(e)}")
                # Continue with other files
                continue
        
        if not loaded_tables:
            context.log.warning("No tables were successfully loaded into PostgreSQL")
            return Output(value=[], metadata={
                "tables_created": 0,
                "message": "No tables loaded"
            })
        
        context.log.info(f"Successfully loaded {len(loaded_tables)} table(s) into PostgreSQL")
        
        return Output(
            value=loaded_tables,
            metadata={
                "tables_created": len(loaded_tables),
                "table_names": [t['table_name'] for t in loaded_tables],
                "total_rows_loaded": sum(t['row_count'] for t in loaded_tables),
                "status": "success"
            }
        )
        
    except Exception as e:
        context.log.error(f"Error loading data into PostgreSQL: {str(e)}")
        raise


@dg.asset(
    kinds={"mongodb"},
    description="Loads all transformed CSV files into MongoDB collections"
)
def load_csv_files_to_mongodb(
    context: AssetExecutionContext,
    mongodb: MongoDBResource,
    transformed_csv_files: List[Dict]
) -> Output[List[Dict]]:
    """
    Step 3d (Load to MongoDB): Loads all transformed DataFrames into MongoDB.
    Creates or replaces collections with sanitized names based on the file names.
    """
    
    if not transformed_csv_files:
        context.log.info("No files to load into MongoDB")
        return Output(value=[], metadata={
            "collections_created": 0,
            "message": "No files to load"
        })
    
    context.log.info(f"Loading {len(transformed_csv_files)} file(s) to MongoDB...")
    
    loaded_collections = []
    
    try:
        for file_data in transformed_csv_files:
            file_name = file_data['output_file_name']
            df = file_data['dataframe']
            
            # Create collection name from file name (sanitize)
            # Remove .csv extension and replace special chars with underscores
            collection_name = file_name.rsplit('.', 1)[0].lower()
            collection_name = ''.join(c if c.isalnum() else '_' for c in collection_name)
            
            # MongoDB collections can start with numbers, but for consistency use same logic
            if collection_name and collection_name[0].isdigit():
                collection_name = f"col_{collection_name}"
            
            context.log.info(f"Loading {file_name} into MongoDB collection '{collection_name}'...")
            
            try:
                # Insert DataFrame into MongoDB (replace if exists)
                doc_count = mongodb.insert_dataframe(
                    collection_name=collection_name,
                    df=df,
                    replace=True
                )
                
                context.log.info(f"  ✓ Collection '{collection_name}' created with {doc_count} documents")
                
                loaded_collections.append({
                    "collection_name": collection_name,
                    "source_file": file_name,
                    "document_count": doc_count,
                    "field_count": len(df.columns)
                })
                
            except Exception as e:
                context.log.error(f"  ✗ Error loading collection '{collection_name}': {str(e)}")
                # Continue with other files
                continue
        
        if not loaded_collections:
            context.log.warning("No collections were successfully loaded into MongoDB")
            return Output(value=[], metadata={
                "collections_created": 0,
                "message": "No collections loaded"
            })
        
        context.log.info(f"Successfully loaded {len(loaded_collections)} collection(s) into MongoDB")
        
        return Output(
            value=loaded_collections,
            metadata={
                "collections_created": len(loaded_collections),
                "collection_names": [c['collection_name'] for c in loaded_collections],
                "total_documents_loaded": sum(c['document_count'] for c in loaded_collections),
                "status": "success"
            }
        )
        
    except Exception as e:
        context.log.error(f"Error loading data into MongoDB: {str(e)}")
        raise


# ============================================================================
# Asset Checks for Loading
# ============================================================================

@asset_check(asset=upload_transformed_csv_files, description="Validates successful file uploads")
def check_upload_success(upload_transformed_csv_files: List[Dict]) -> AssetCheckResult:
    """Check that all files were successfully uploaded to Google Drive."""
    if not upload_transformed_csv_files:
        return AssetCheckResult(
            passed=True,
            description="No files to upload (empty input)",
            severity=AssetCheckSeverity.WARN
        )
    
    # Separate successful and failed uploads
    successful_uploads = [f for f in upload_transformed_csv_files if f.get('status') == 'success']
    failed_uploads = [f for f in upload_transformed_csv_files if f.get('status') == 'failed']
    
    if failed_uploads:
        return AssetCheckResult(
            passed=False,
            description=f"{len(failed_uploads)}/{len(upload_transformed_csv_files)} file(s) failed to upload",
            severity=AssetCheckSeverity.ERROR,
            metadata={
                "failed_count": len(failed_uploads),
                "failed_files": [f.get('file_name', 'unknown') for f in failed_uploads],
                "error_messages": [f.get('error', 'Unknown error') for f in failed_uploads],
                "successful_count": len(successful_uploads)
            }
        )
    
    return AssetCheckResult(
        passed=True,
        description=f"All {len(upload_transformed_csv_files)} files uploaded successfully",
        metadata={
            "files_uploaded": len(upload_transformed_csv_files),
            "files_created": len([f for f in upload_transformed_csv_files if f.get('action') == 'created']),
            "files_replaced": len([f for f in upload_transformed_csv_files if f.get('action') == 'replaced'])
        }
    )


@asset_check(asset=load_csv_files_to_duckdb, description="Validates DuckDB table creation")
def check_duckdb_loading(load_csv_files_to_duckdb: List[Dict]) -> AssetCheckResult:
    """Check that all tables were successfully created in DuckDB."""
    if not load_csv_files_to_duckdb:
        return AssetCheckResult(
            passed=True,
            description="No tables to create (empty input)",
            severity=AssetCheckSeverity.WARN
        )
    
    # Check if any tables are missing required fields (indicating failure)
    failed_tables = []
    for table_info in load_csv_files_to_duckdb:
        # A successful table should have: table_name, row_count, and column_count
        if not all(key in table_info for key in ['table_name', 'row_count', 'column_count']):
            failed_tables.append(table_info.get('table_name', 'unknown'))
    
    if failed_tables:
        return AssetCheckResult(
            passed=False,
            description=f"{len(failed_tables)} table(s) failed to create: {failed_tables}",
            severity=AssetCheckSeverity.ERROR
        )
    
    total_rows = sum(t.get('row_count', 0) for t in load_csv_files_to_duckdb)
    return AssetCheckResult(
        passed=True,
        description=f"All {len(load_csv_files_to_duckdb)} tables created successfully",
        metadata={
            "tables_created": len(load_csv_files_to_duckdb),
            "total_rows_loaded": total_rows
        }
    )


@asset_check(asset=load_csv_files_to_postgresql, description="Validates PostgreSQL table creation")
def check_postgresql_loading(load_csv_files_to_postgresql: List[Dict]) -> AssetCheckResult:
    """Check that all tables were successfully created in PostgreSQL."""
    if not load_csv_files_to_postgresql:
        return AssetCheckResult(
            passed=True,
            description="No tables to create (empty input)",
            severity=AssetCheckSeverity.WARN
        )
    
    # Check if any tables are missing required fields (indicating failure)
    failed_tables = []
    for table_info in load_csv_files_to_postgresql:
        # A successful table should have: table_name, row_count, and column_count
        if not all(key in table_info for key in ['table_name', 'row_count', 'column_count']):
            failed_tables.append(table_info.get('table_name', 'unknown'))
    
    if failed_tables:
        return AssetCheckResult(
            passed=False,
            description=f"{len(failed_tables)} table(s) failed to create: {failed_tables}",
            severity=AssetCheckSeverity.ERROR
        )
    
    total_rows = sum(t.get('row_count', 0) for t in load_csv_files_to_postgresql)
    return AssetCheckResult(
        passed=True,
        description=f"All {len(load_csv_files_to_postgresql)} tables created successfully",
        metadata={
            "tables_created": len(load_csv_files_to_postgresql),
            "total_rows_loaded": total_rows
        }
    )


@asset_check(asset=load_csv_files_to_mongodb, description="Validates MongoDB collection creation")
def check_mongodb_loading(load_csv_files_to_mongodb: List[Dict]) -> AssetCheckResult:
    """Check that all collections were successfully created in MongoDB."""
    if not load_csv_files_to_mongodb:
        return AssetCheckResult(
            passed=True,
            description="No collections to create (empty input)",
            severity=AssetCheckSeverity.WARN
        )
    
    # Check if any collections are missing required fields (indicating failure)
    failed_collections = []
    for collection_info in load_csv_files_to_mongodb:
        # A successful collection should have: collection_name and document_count
        if not all(key in collection_info for key in ['collection_name', 'document_count']):
            failed_collections.append(collection_info.get('collection_name', 'unknown'))
    
    if failed_collections:
        return AssetCheckResult(
            passed=False,
            description=f"{len(failed_collections)} collection(s) failed to create: {failed_collections}",
            severity=AssetCheckSeverity.ERROR
        )
    
    total_docs = sum(c.get('document_count', 0) for c in load_csv_files_to_mongodb)
    return AssetCheckResult(
        passed=True,
        description=f"All {len(load_csv_files_to_mongodb)} collections created successfully",
        metadata={
            "collections_created": len(load_csv_files_to_mongodb),
            "total_documents_loaded": total_docs
        }
    )
