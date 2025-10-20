"""Transformation and Cleaning Assets

This module contains assets responsible for:
- Data transformation and cleaning
- Column normalization
- Data type handling
- Missing value treatment
- Data validation
"""

import pandas as pd

import dagster as dg
from dagster import AssetExecutionContext, Output

from typing import List, Dict


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
                            .str.normalize('NFKD')                        # Split accent marks
                            .str.encode('utf-8', errors='ignore')  # encode as utf-8
                            .str.decode('utf-8')             # decode as utf-8
                            .str.upper()                           # Normalize to uppercase
                            .str.replace(r'[^A-Z0-9@/\s\.\-_]', '', regex=True) # Keep @, /, ., -, _  remove special chars
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
            varying_cols = [col for col in df.columns if df[col].nunique(dropna=False) > 2]
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
