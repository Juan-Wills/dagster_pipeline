"""Top-level Dagster definitions loader

This file should assemble assets, jobs, resources, schedules, and sensors
into objects Dagster can discover via `workspace.yaml`.
"""

# Example placeholder imports
from dagster import Definitions, AssetsDefinition
from pipeline.assets import test
from pipeline.jobs import *
from pipeline.resources import DatabaseResource
from pipeline.schedules import *
from pipeline.sensors import *

# Create the Definitions object - Dagster will discover this
defs = Definitions(
    assets=[test.hi],
    # jobs=[],
    # resources={},
    # schedules=[],
    # sensors=[],
)
