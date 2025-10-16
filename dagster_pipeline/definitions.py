"""Top-level Dagster definitions loader

This file should assemble assets, jobs, resources, schedules, and sensors
into objects Dagster can discover via `workspace.yaml`.
"""

import os
from dagster import Definitions
from dagster_pipeline.assets.google_drive_etl import process_drive_files
from dagster_pipeline.resources import GoogleDriveResource
from dagster_pipeline.sensors import google_drive_new_file_sensor
from config import CREDENTIALS_PATH, TOKEN_PATH

# Get the project root directory (parent of pipeline directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Create the Definitions object - Dagster will discover this
defs = Definitions(
    assets=[process_drive_files],
    resources={
        "google_drive": GoogleDriveResource(
            credentials_path=str(CREDENTIALS_PATH),
            token_path=str(TOKEN_PATH),
            scopes=["https://www.googleapis.com/auth/drive"]
        )
    },
    sensors=[google_drive_new_file_sensor],
)
