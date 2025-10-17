import pandas as pd
from dagster import asset, AssetExecutionContext
import dagster as dg
from dagster_duckdb import DuckDBResource
import os
from pathlib import Path


#path for the origin file csv
CSV_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "002_victimsmuestra.csv"

@dg.asset(
    kinds={"csv"},
    description="Reads the original CSV (ISO-8859-1, sep='»') and loads it into a DataFrame."
)
def extracted_samples_df(context: AssetExecutionContext) -> pd.DataFrame:
    """
    Step 1 (Extraction): Reads the original file and converts it to a pandas DataFrame.
    """
    context.log.info(f"Extracting data from: {CSV_PATH}")

    df = pd.read_csv(
        CSV_PATH,
        sep='»',
        encoding='ISO-8859-1',
        engine='python'
    )
    
    context.log.info("Extraction completed. Data loaded into memory.")
    
    # Return the DataFrame so Dagster can pass it to the next asset.
    return df


@dg.asset(
    kinds={"pandas"},
    description="Transforms the data types, cleans missing values, and returns the transformed DataFrame."
)

def transformed_samples_df(context: AssetExecutionContext, extracted_samples_df: pd.DataFrame):

    """
    Returns the transformed DataFrame for use in the next steps.
    Includes:
    - Column name normalization
    - Removal of highly missing columns
    - Filling missing values in string and numeric columns
    - Removal of constant columns
    """

    df = extracted_samples_df.copy()

    # Convert all column names to uppercase
    context.log.info("Converting column names to uppercase...")
    df.columns = df.columns.str.upper()
    context.log.info(f"New column names: {list(df.columns)}")

    # Remove columns with more than 90% missing values
    threshold = len(df) * 0.1
    cols_before = df.shape[1]
    df = df.dropna(axis=1, thresh=threshold)
    cols_after = df.shape[1]
    context.log.info(f"Removed {cols_before - cols_after} columns with >90% missing values.")
    #Fill missing values for remaining columns
    context.log.info("Filling missing values...")

    #Clean strings — remove extra spaces, newlines, and normalize case
    context.log.info("Cleaning extra spaces, newlines, and normalizing case...")
    for col in df.select_dtypes(include=['object', 'string']).columns:
        df[col] = (
            df[col]
            .astype(str)                     # Ensure string type
            .str.strip()                     # Remove leading/trailing spaces
            .str.replace(r'\s+', ' ', regex=True)  # Replace multiple spaces/newlines with single space
            .str.upper()                     # Normalize to uppercase
        )
    context.log.info("String normalization completed ")

    # Fill string or object columns with empty string
    for col in df.select_dtypes(include=['object', 'string']).columns:
        df[col] = df[col].fillna("NA")

    df = df.replace({
    'nan': 'NA',        # Texto 'nan'
    'NAN': 'NA',        # Texto 'NaN' en mayúsculas
    'None': 'NA',       # Texto 'None'
    '': 'NA',           # Vacío exacto
    ' ': 'NA',          # Un espacio
    '  ': 'NA',         # Dos espacios
    }, regex=False)
    context.log.info("Null-like values replaced.")


    # Fill numeric columns with 0
    for col in df.select_dtypes(include=['float', 'int']).columns:
        df[col] = df[col].fillna(0)
    context.log.info("Data cleaning completed successfully ")

    #Remove constant columns
    n_before = df.shape[1]
    df = df.loc[:, df.nunique(dropna=False) > 1]
    n_after = df.shape[1]
    context.log.info(f"Removed {n_before - n_after} constant columns.")

    return df


@dg.asset(
    kinds={"csv"},
    description="Saves the transformed DataFrame to a CSV file."
)
def save_transformed_csv(context: AssetExecutionContext, transformed_samples_df: pd.DataFrame):

    """
    Saves the already transformed DataFrame.
    """
    destination_path = "data/processed/muestras_500_1.csv"
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    
    transformed_samples_df.to_csv(
        destination_path,
        encoding='utf-8',
        sep='|',
        index=False
    )
    context.log.info("File saved successfully!")


@dg.asset(
    kinds={"duckdb"},
)
def load_csv_to_duckdb(
    context: AssetExecutionContext,
    duckdb: DuckDBResource,
    transformed_samples_df: pd.DataFrame,
):   
    try:
        with duckdb.get_connection() as conn:

            conn.register('temp_data', transformed_samples_df)
            create_query=f"""
                CREATE OR REPLACE TABLE my_prueba AS



                
                SELECT * FROM transformed_samples_df
            """
            conn.execute(create_query)

            # Verify the charge
            row_count=conn.execute("SELECT COUNT(*) FROM my_prueba").fetchone()[0]
            column_count = conn.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'my_prueba'").fetchone()[0]
            context.log.info(f"Successfully loaded {row_count} rows and {column_count} columns into my_prueba table")

    except Exception as e:
        context.log.error(f"Error loading data into DuckDB: {str(e)}")
        raise