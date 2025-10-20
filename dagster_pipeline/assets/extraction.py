"""Extraction and Loading Assets

This module contains assets responsible for:
- Extracting data from external sources (Google Drive)
- Loading raw data into memory
- Initial file parsing and validation
"""

import pandas as pd

import dagster as dg
from dagster import AssetExecutionContext, Output
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
