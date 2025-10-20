import pandas as pd
import io

import dagster as dg
from dagster import AssetExecutionContext, Output
from dagster_pipeline.resources.duckdb_connection import DuckDBResource
from dagster_pipeline.resources.google_drive_resource import GoogleDriveResource

from typing import List, Dict


@dg.asset(
    kinds={"google_drive", "csv"},
    description="Downloads CSV files from Google Drive raw_data folder and performs initial extraction"
)
def extracted_csv_files(
    context: AssetExecutionContext,
    google_drive: GoogleDriveResource
) -> Output[List[Dict]]:
    """
    Step 1 (Extraction): Downloads ALL CSV files from Google Drive raw_data folder.
    Tries multiple encoding and separator combinations to handle different file formats.
    Returns a list of DataFrames with their metadata.
    """
    
    # Find raw_data folder
    context.log.info("Searching for 'raw_data' folder in Google Drive...")
    raw_folder_id = google_drive.find_folder_by_name("raw_data")
    
    if not raw_folder_id:
        context.log.error("'raw_data' folder not found in Google Drive")
        raise ValueError("'raw_data' folder not found in Google Drive")
    
    context.log.info(f"Found 'raw_data' folder (ID: {raw_folder_id})")
    
    # List CSV files in raw_data folder
    files = google_drive.list_files_in_folder(raw_folder_id, mime_type='text/csv')
    
    if not files:
        context.log.error("No CSV files found in 'raw_data' folder")
        raise ValueError("No CSV files found in 'raw_data' folder")
    
    context.log.info(f"Found {len(files)} CSV file(s) to process")
    
    extracted_data = []
    
    # Common separators and encodings to try
    separators = ['»', ',', ';', '|', '\t']
    encodings = ['ISO-8859-1', 'utf-8', 'latin-1', 'cp1252']
    
    for file in files:
        file_id = file['id']
        file_name = file['name']
        
        context.log.info(f"Downloading file: {file_name}")
        
        # Get file content directly into memory
        file_content = google_drive.get_file_content(file_id)
        context.log.info(f"  File loaded into memory")
        
        # Try to read CSV with different combinations
        df = None
        parse_info = {'separator': None, 'encoding': None}
        chunk_size = 100000  # Read in chunks of 100,000 rows
        
        for encoding in encodings:
            for separator in separators:
                try:
                    # Reset file pointer
                    file_content.seek(0)
                    
                    # Read CSV in chunks
                    chunks = []
                    chunk_reader = pd.read_csv(
                        file_content,
                        sep=separator,
                        encoding=encoding,
                        engine='python',
                        on_bad_lines='skip',  # Skip problematic lines
                        chunksize=chunk_size
                    )
                    
                    for i, chunk in enumerate(chunk_reader):
                        context.log.info(f"  Processing chunk {i+1} ({len(chunk)} rows)")
                        chunks.append(chunk)
                    
                    # Concatenate all chunks
                    if chunks:
                        df = pd.concat(chunks, ignore_index=True)
                        context.log.info(f"  Combined {len(chunks)} chunk(s) into DataFrame")
                    
                    # Validate: must have at least 1 column and 1 row
                    if df is not None and len(df.columns) > 0 and len(df) > 0:
                        parse_info = {'separator': separator, 'encoding': encoding}
                        context.log.info(f"  Successfully parsed with sep='{separator}', encoding='{encoding}'")
                        break
                        
                except Exception as e:
                    continue
            
            if df is not None and len(df.columns) > 0:
                break
        
        # If all attempts failed, try with default pandas inference
        if df is None or len(df.columns) == 0:
            context.log.warning(f"  Standard parsers failed. Trying pandas auto-detection...")
            try:
                file_content.seek(0)
                # Read with chunking even for auto-detection
                chunks = []
                chunk_reader = pd.read_csv(
                    file_content, 
                    engine='python', 
                    on_bad_lines='skip',
                    chunksize=chunk_size
                )
                
                for i, chunk in enumerate(chunk_reader):
                    context.log.info(f"  Processing chunk {i+1} ({len(chunk)} rows)")
                    chunks.append(chunk)
                
                if chunks:
                    df = pd.concat(chunks, ignore_index=True)
                
                parse_info = {'separator': 'auto', 'encoding': 'auto'}
                context.log.info(f"  Parsed with auto-detection")
            except Exception as e:
                context.log.error(f"  Failed to parse {file_name}: {str(e)}")
                continue
        
        if df is not None and len(df) > 0:
            context.log.info(f"  Loaded {len(df)} rows with {len(df.columns)} columns")
            
            # Store the DataFrame with metadata
            extracted_data.append({
                'file_name': file_name,
                'dataframe': df,
                'row_count': len(df),
                'column_count': len(df.columns),
                'parse_info': parse_info
            })
        else:
            context.log.error(f"  Skipping {file_name}: Could not parse or empty file")
    
    if not extracted_data:
        raise ValueError("No files could be successfully parsed")
    
    context.log.info(f"Extraction completed. Successfully processed {len(extracted_data)}/{len(files)} file(s)")
    
    return Output(
        value=extracted_data,
        metadata={
            "files_extracted": len(extracted_data),
            "total_rows": sum(f['row_count'] for f in extracted_data),
            "file_names": [f['file_name'] for f in extracted_data]
        }
    )


@dg.asset(
    kinds={"pandas"},
    description="Transforms all extracted CSV files with data cleaning and normalization"
)
def transformed_csv_files(
    context: AssetExecutionContext, 
    extracted_csv_files: List[Dict]
) -> Output[List[Dict]]:
    """
    Step 2 (Transformation): Transforms all extracted DataFrames with robust error handling.
    Tolerates different data types and formats.
    Includes:
    - Column name normalization (with fallback for unnamed columns)
    - Removal of highly missing columns (configurable threshold)
    - Safe string cleaning (handles mixed types)
    - Filling missing values adaptively
    - Removal of constant/duplicate columns
    """
    
    transformed_data = []
    
    for file_data in extracted_csv_files:
        file_name = file_data['file_name']
        df = file_data['dataframe'].copy()
        
        context.log.info(f"Transforming file: {file_name} ({len(df)} rows, {len(df.columns)} columns)")
        
        try:
            # 1. Handle unnamed/duplicate columns
            context.log.info(f"  Normalizing column names...")
            new_columns = []
            seen_names = {}
            
            for i, col in enumerate(df.columns):
                # Convert to string and handle empty/null column names
                col_str = str(col).strip() if pd.notna(col) and str(col).strip() else f"COLUMN_{i}"
                
                # Make uppercase
                col_upper = col_str.upper()
                
                # Handle duplicates
                if col_upper in seen_names:
                    seen_names[col_upper] += 1
                    col_upper = f"{col_upper}_{seen_names[col_upper]}"
                else:
                    seen_names[col_upper] = 0
                
                new_columns.append(col_upper)
            
            df.columns = new_columns
            context.log.info(f"  Column names normalized: {len(df.columns)} columns")

            # 2. Remove columns with excessive missing values (>90%)
            threshold = max(1, int(len(df) * 0.1))  # At least 1 row
            cols_before = df.shape[1]
            df = df.dropna(axis=1, thresh=threshold)
            cols_after = df.shape[1]
            
            if cols_before > cols_after:
                context.log.info(f"  Removed {cols_before - cols_after} columns with >90% missing values")
            
            # 3. Identify column types more robustly
            string_cols = []
            numeric_cols = []
            
            for col in df.columns:
                # Try to infer if column is actually numeric despite object dtype
                try:
                    pd.to_numeric(df[col], errors='coerce')
                    # If more than 50% can be converted to numeric, treat as numeric
                    numeric_count = pd.to_numeric(df[col], errors='coerce').notna().sum()
                    if numeric_count / len(df) > 0.5:
                        numeric_cols.append(col)
                    else:
                        string_cols.append(col)
                except:
                    string_cols.append(col)
            
            context.log.info(f"  Identified {len(string_cols)} string and {len(numeric_cols)} numeric columns")
            
            # 4. Clean string columns safely
            if string_cols:
                context.log.info(f"  Cleaning string columns...")
                for col in string_cols:
                    try:
                        df[col] = (
                            df[col]
                            .astype(str)                           # Convert to string
                            .str.strip()                           # Remove leading/trailing spaces
                            .str.replace(r'\s+', ' ', regex=True)  # Collapse whitespace
                            .str.upper()                           # Normalize to uppercase
                        )
                        
                        # Replace null-like strings with NA
                        df[col] = df[col].replace({
                            'NAN': 'NA',
                            'NONE': 'NA',
                            'NULL': 'NA',
                            '': 'NA',
                            ' ': 'NA',
                        })
                        
                        # Fill remaining NaN values
                        df[col] = df[col].fillna("NA")
                        
                    except Exception as e:
                        context.log.warning(f"  Warning: Could not clean column '{col}': {str(e)}")
                        # Fill with NA as fallback
                        df[col] = df[col].fillna("NA")

            # 5. Handle numeric columns
            if numeric_cols:
                context.log.info(f"  Processing numeric columns...")
                for col in numeric_cols:
                    try:
                        # Try to convert to numeric
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        # Fill NaN with 0
                        df[col] = df[col].fillna(0)
                    except Exception as e:
                        context.log.warning(f"  Warning: Could not process numeric column '{col}': {str(e)}")
                        df[col] = df[col].fillna(0)

            # 6. Remove completely empty rows (all NA or 0)
            rows_before = len(df)
            # Consider a row empty if all string columns are "NA" and all numeric columns are 0
            df = df[~((df[string_cols] == 'NA').all(axis=1) if string_cols else False)]
            rows_after = len(df)
            
            if rows_before > rows_after:
                context.log.info(f"  Removed {rows_before - rows_after} completely empty rows")

            # 7. Remove constant columns (all values the same)
            cols_before = df.shape[1]
            varying_cols = [col for col in df.columns if df[col].nunique(dropna=False) > 1]
            df = df[varying_cols]
            cols_after = df.shape[1]
            
            if cols_before > cols_after:
                context.log.info(f"  Removed {cols_before - cols_after} constant columns")
            
            # 8. Remove duplicate columns (same content, different name)
            cols_before = df.shape[1]
            df = df.T.drop_duplicates().T
            cols_after = df.shape[1]
            
            if cols_before > cols_after:
                context.log.info(f"  Removed {cols_before - cols_after} duplicate columns")
            
            # Final validation
            if len(df) == 0 or len(df.columns) == 0:
                context.log.warning(f"  Skipping {file_name}: No data remaining after transformation")
                continue
            
            context.log.info(f"  Transformation completed: {len(df)} rows, {len(df.columns)} columns")
            
            # Generate output filename
            base_name = file_name.rsplit('.', 1)[0]
            output_name = f"{base_name}_transformed.csv"
            
            transformed_data.append({
                'original_file_name': file_name,
                'output_file_name': output_name,
                'dataframe': df,
                'row_count': len(df),
                'column_count': len(df.columns)
            })
            
        except Exception as e:
            context.log.error(f"  Error transforming {file_name}: {str(e)}")
            context.log.warning(f"  Skipping {file_name} due to transformation error")
            continue

    if not transformed_data:
        raise ValueError("No files could be successfully transformed")

    context.log.info(f"All transformations completed. Successfully processed {len(transformed_data)}/{len(extracted_csv_files)} file(s)")
    
    return Output(
        value=transformed_data,
        metadata={
            "files_transformed": len(transformed_data),
            "total_rows": sum(f['row_count'] for f in transformed_data),
            "file_names": [f['output_file_name'] for f in transformed_data]
        }
    )


@dg.asset(
    kinds={"google_drive", "csv"},
    description="Uploads all transformed CSV files to Google Drive processed_data folder",
    deps=["transformed_csv_files"]
)
def upload_transformed_csv_files(
    context: AssetExecutionContext,
    google_drive: GoogleDriveResource,
    transformed_csv_files: List[Dict]
) -> Output[List[Dict]]:
    """
    Step 3 (Upload): Uploads all transformed DataFrames to Google Drive.
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
                'name': uploaded['name'],
                'id': uploaded['id'],
                'action': action
            })
        except Exception as e:
            context.log.error(f"  ✗ Error uploading {file_name}: {str(e)}")
    
    context.log.info(
        f"Upload completed. {len(uploaded_files)} file(s) uploaded "
        f"({created_count} new, {replaced_count} replaced)"
    )
    
    return Output(
        value=uploaded_files,
        metadata={
            "files_uploaded": len(uploaded_files),
            "files_created": created_count,
            "files_replaced": replaced_count,
            "file_names": [f['name'] for f in uploaded_files],
            "total_rows": sum(f['row_count'] for f in transformed_csv_files)
        }
    )


@dg.asset(
    kinds={"duckdb"},
    description="Loads all transformed CSV files into DuckDB tables",
    deps=["transformed_csv_files"]
)
def load_csv_files_to_duckdb(
    context: AssetExecutionContext,
    duckdb: DuckDBResource,
    transformed_csv_files: List[Dict]
) -> Output[List[Dict]]:
    """
    Step 4 (Load): Loads all transformed DataFrames into DuckDB.
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