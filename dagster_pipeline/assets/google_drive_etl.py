"""Google Drive ETL Assets

Assets for downloading, processing, and uploading files from/to Google Drive.
"""

import os
import pandas as pd
from typing import List
from dagster import asset, AssetExecutionContext, Output
from dagster_pipeline.resources.google_drive_resource import GoogleDriveResource
from config import RAW_DATA_DIR, PROCESSED_DATA_DIR


@asset(
    description="Download CSV files from Google Drive raw_data folder and upload to processed_data folder"
)
def process_drive_files(
    context: AssetExecutionContext,
    google_drive: GoogleDriveResource
) -> Output[List[str]]:
    """
    Download files from raw_data, process (currently just pass-through),
    and upload to processed_data folder in Google Drive.
    """
    
    # Find raw_data folder
    context.log.info("Searching for 'raw_data' folder in Google Drive...")
    raw_folder_id = google_drive.find_folder_by_name("raw_data")
    
    if not raw_folder_id:
        context.log.error("'raw_data' folder not found in Google Drive")
        return Output(value=[], metadata={
            "error": "raw_data folder not found"
        })
    
    context.log.info(f"Found 'raw_data' folder (ID: {raw_folder_id})")
    
    # List CSV files in raw_data folder
    files = google_drive.list_files_in_folder(raw_folder_id, mime_type='text/csv')
    
    if not files:
        context.log.info("No CSV files found in 'raw_data' folder")
        return Output(value=[], metadata={
            "files_processed": 0,
            "message": "No files to process"
        })
    
    context.log.info(f"Found {len(files)} CSV file(s) to process")
    
    # Download files - use absolute paths from config
    download_folder = str(RAW_DATA_DIR)
    processed_folder = str(PROCESSED_DATA_DIR)
    os.makedirs(processed_folder, exist_ok=True)
    
    processed_files = []
    
    for file in files:
        file_id = file['id']
        file_name = file['name']
        
        context.log.info(f"Processing: {file_name}")
        
        # Download file
        local_path = google_drive.download_file(file_id, file_name, download_folder)
        context.log.info(f"  Downloaded to: {local_path}")
        
        # Process file with transformations
        # Ensure the file has .csv extension for processed output
        if not file_name.lower().endswith('.csv'):
            processed_file_name = f"{file_name}.csv"
        else:
            processed_file_name = file_name
            
        processed_path = os.path.join(processed_folder, processed_file_name)

        # Add your transformations here
        df = pd.read_csv(local_path)
        context.log.info(f"  Loaded {len(df)} rows with columns: {list(df.columns)}")
        
        # Clean data - remove rows with any missing values
        initial_rows = len(df)
        df = df.dropna()
        context.log.info(f"  Removed {initial_rows - len(df)} rows with missing data")
        
        # Example transformations (customize based on your needs):
        # For employee data: Calculate annual bonus (10% of salary)
        if 'Salary' in df.columns:
            df['AnnualBonus'] = df['Salary'] * 0.10
            context.log.info(f"  Added 'AnnualBonus' column")
        
        # Save processed data
        df.to_csv(processed_path, index=False)
        context.log.info(f"  Saved {len(df)} rows to: {processed_path}")
        
        context.log.info(f"  Processed file saved to: {processed_path}")
        processed_files.append(processed_file_name)
    
    # Upload processed files to Google Drive
    context.log.info("Uploading processed files to Google Drive...")
    
    # Create or find processed_data folder in Google Drive
    processed_folder_id = google_drive.create_folder_if_not_exists("processed_data")
    context.log.info(f"Using 'processed_data' folder (ID: {processed_folder_id})")
    
    uploaded_files = []
    for file_name in processed_files:
        file_path = os.path.join(processed_folder, file_name)
        
        try:
            uploaded = google_drive.upload_file(file_path, processed_folder_id)
            context.log.info(f"  Uploaded: {uploaded['name']} (ID: {uploaded['id']})")
            uploaded_files.append(uploaded['name'])
        except Exception as e:
            context.log.error(f"  Error uploading {file_name}: {e}")
    
    return Output(
        value=uploaded_files,
        metadata={
            "files_downloaded": len(files),
            "files_processed": len(processed_files),
            "files_uploaded": len(uploaded_files),
            "file_names": uploaded_files
        }
    )
