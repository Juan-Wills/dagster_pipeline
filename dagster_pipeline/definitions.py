"""Top-level Dagster definitions loader

This file should assemble assets, jobs, resources, schedules, and sensors
into objects Dagster can discover via `workspace.yaml`.
"""

import os
from dagster_pipeline.assets import google_drive_etl, prueba
from dagster_pipeline.resources import GoogleDriveResource, database_resource
from dagster_pipeline.sensors import google_drive_new_file_sensor
from config import CREDENTIALS_PATH, TOKEN_PATH
#definitions_prueba
from dagster import Definitions, load_assets_from_modules
from dagster_pipeline.resources.duckdb_connection import database_resource


# Get the project root directory (parent of pipeline directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
all_assets=load_assets_from_modules([prueba,google_drive_etl])

# Create the Definitions object - Dagster will discover this
defs = Definitions(
    assets=all_assets,
    resources={
        "google_drive": GoogleDriveResource(
            credentials_path=str(CREDENTIALS_PATH),
            token_path=str(TOKEN_PATH),
            scopes=["https://www.googleapis.com/auth/drive"]
        ),
        "duckdb":database_resource,
    },
    sensors=[google_drive_new_file_sensor],
)
