"""Assets package

This package should import and register Dagster assets.
"""

# Import all assets from google_drive_etl.py (main pipeline)
from .google_drive_etl import (
    extracted_csv_files,
    transformed_csv_files,
    upload_transformed_csv_files,
    load_csv_files_to_duckdb
)

__all__ = [
    "extracted_csv_files",
    "transformed_csv_files",
    "upload_transformed_csv_files",
    "load_csv_files_to_duckdb"
]
