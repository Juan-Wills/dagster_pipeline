"""Configuration module for dagster_pipeline

Contains settings, constants, and configuration loaders.
"""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Configuration paths
CONFIG_DIR = PROJECT_ROOT / "config"
DAGSTER_CONFIG = CONFIG_DIR / "dagster.yaml"
WORKSPACE_CONFIG = CONFIG_DIR / "workspace.yaml"

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
TEMP_DATA_DIR = DATA_DIR / "temp"

# Auth directory
AUTH_DIR = PROJECT_ROOT / "auth"
CREDENTIALS_PATH = AUTH_DIR / "credentials.json"
TOKEN_PATH = AUTH_DIR / "token.json"

# Ensure directories exist
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, TEMP_DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
