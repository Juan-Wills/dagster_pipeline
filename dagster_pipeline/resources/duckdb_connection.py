import dagster as dg
from dagster_duckdb import DuckDBResource
from pathlib import Path
import os


#Path absolute to the database
DUCKDB_PATH = Path(__file__).resolve().parents[2] / "data" / "duckdb" / "prueba.duckdb"
os.makedirs(DUCKDB_PATH.parent, exist_ok=True)
database_resource = DuckDBResource(database=str(DUCKDB_PATH))

#Define the resource of the conexion
