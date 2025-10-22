"""Top-level Dagster definitions loader

This file should assemble assets, jobs, resources, schedules, and sensors
into objects Dagster can discover via `workspace.yaml`.
"""

import os
from dagster_pipeline.assets import extraction, transformation, loading
from dagster_pipeline.resources import GoogleDriveResource, database_resource, PostgreSQLResource, MongoDBResource
from dagster_pipeline.sensors import google_drive_new_file_sensor
from config import CREDENTIALS_PATH, TOKEN_PATH
from dagster import Definitions, load_assets_from_modules, load_asset_checks_from_modules
from dagster_pipeline.resources.duckdb_connection import database_resource


# Get the project root directory (parent of pipeline directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load assets and asset checks from organized modules
all_assets = load_assets_from_modules([extraction, transformation, loading])
all_asset_checks = load_asset_checks_from_modules([extraction, transformation, loading])

# Create the Definitions object - Dagster will discover this
defs = Definitions(
    assets=all_assets,
    asset_checks=all_asset_checks,
    resources={
        "google_drive": GoogleDriveResource(
            credentials_path=str(CREDENTIALS_PATH),
            token_path=str(TOKEN_PATH),
            scopes=["https://www.googleapis.com/auth/drive"]
        ),
        "duckdb": database_resource,
        "postgresql": PostgreSQLResource(
            host=os.getenv("POSTGRES_HOST", "postgres"),  # Use 'postgres' inside Docker
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "dagster_pipeline"),
            user=os.getenv("POSTGRES_USER", "juan-wills"),
            password=os.getenv("POSTGRES_PASSWORD", "juan1234")
        ),
        "mongodb": MongoDBResource(
            host=os.getenv("MONGO_HOST", "mongodb"),  # Use 'mongodb' inside Docker
            port=int(os.getenv("MONGO_PORT", "27017")),
            database=os.getenv("MONGO_DB", "dagster_pipeline"),
            username=os.getenv("MONGO_ROOT_USER", "juan-wills"),
            password=os.getenv("MONGO_ROOT_PASSWORD", "juan1234"),
            auth_source=os.getenv("MONGO_AUTH_SOURCE", "admin")
        ),
    },
    sensors=[google_drive_new_file_sensor],
)
