import dagster as dg
from dagster_duckdb import DuckDBResource
from pathlib import Path


#Path absolute to the database
DUCKDB_PATH = Path(__file__).resolve().parents[3] / "data" / "duckdb" / "prueba.duckdb"

#Define the resource of the conexion
database_resource = DuckDBResource(database=str(DUCKDB_PATH))
