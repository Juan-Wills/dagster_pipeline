"""Assets package

This package should import and register Dagster assets.
"""

from .google_drive_etl import process_drive_files

__all__ = ["process_drive_files"]
