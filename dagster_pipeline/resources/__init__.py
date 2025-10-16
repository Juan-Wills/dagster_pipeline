"""Resources package

Place resource factories and instances here.
"""

from .database_resource import DatabaseResource
from .google_drive_resource import GoogleDriveResource

__all__ = ["DatabaseResource", "GoogleDriveResource"]
