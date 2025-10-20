"""Assets package

This package imports and registers Dagster assets organized by category:
1. Extraction: Loading and extracting data from external sources
2. Transformation: Cleaning and transforming data
3. Loading: Persisting data to destination systems
"""

# Category 1: Extraction and Loading from external sources
from .extraction import (
    extracted_csv_files,
)

# Category 2: Transformation and Cleaning
from .transformation import (
    transformed_csv_files,
)

# Category 3: Loading to destination systems
from .loading import (
    upload_transformed_csv_files,
    load_csv_files_to_duckdb,
    load_csv_files_to_postgresql,
    load_csv_files_to_mongodb,
)

__all__ = [
    # Extraction assets
    "extracted_csv_files",
    
    # Transformation assets
    "transformed_csv_files",
    
    # Loading assets
    "upload_transformed_csv_files",
    "load_csv_files_to_duckdb",
    "load_csv_files_to_postgresql",
    "load_csv_files_to_mongodb",
]
