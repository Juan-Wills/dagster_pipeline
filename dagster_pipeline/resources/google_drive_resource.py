"""Google Drive resource for Dagster

Handles authentication and interactions with Google Drive API.
"""

import os
import io
from typing import List, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

from dagster import ConfigurableResource
from pydantic import Field


class GoogleDriveResource(ConfigurableResource):
    """Resource for interacting with Google Drive API."""
    
    credentials_path: str = Field(
        default="auth/credentials.json",
        description="Path to the Google API credentials JSON file"
    )
    token_path: str = Field(
        default="auth/token.json",
        description="Path to store the access token"
    )
    scopes: List[str] = Field(
        default=["https://www.googleapis.com/auth/drive"],
        description="Google Drive API scopes"
    )
    
    def _get_credentials(self) -> Credentials:
        """Get or refresh Google Drive credentials."""
        creds = None
        
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.scopes
                )
                creds = flow.run_local_server(port=0)
            
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
        
        return creds
    
    def get_service(self):
        """Build and return the Google Drive service."""
        creds = self._get_credentials()
        return build("drive", "v3", credentials=creds)
    
    def find_folder_by_name(self, folder_name: str) -> Optional[str]:
        """Find a folder by name in Google Drive."""
        service = self.get_service()
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        items = results.get('files', [])
        if not items:
            return None
        
        return items[0]['id']
    
    def list_files_in_folder(self, folder_id: str, mime_type: Optional[str] = None) -> List[Dict]:
        """List all files in a specific folder."""
        service = self.get_service()
        
        query = f"'{folder_id}' in parents and trashed=false"
        if mime_type:
            query += f" and mimeType='{mime_type}'"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType, modifiedTime, size)'
        ).execute()
        
        return results.get('files', [])
    
    def download_file(self, file_id: str, file_name: str, download_path: str) -> str:
        """Download a file from Google Drive."""
        service = self.get_service()
        
        os.makedirs(download_path, exist_ok=True)
        file_path = os.path.join(download_path, file_name)
        
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        with open(file_path, 'wb') as f:
            f.write(fh.getvalue())
        
        return file_path
    
    def create_folder_if_not_exists(self, folder_name: str) -> str:
        """Create a folder in Google Drive if it doesn't exist."""
        folder_id = self.find_folder_by_name(folder_name)
        
        if folder_id:
            return folder_id
        
        service = self.get_service()
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        
        return folder.get('id')
    
    def upload_file(self, file_path: str, folder_id: str, mime_type: str = 'text/csv') -> Dict:
        """Upload a file to a Google Drive folder."""
        service = self.get_service()
        
        file_name = os.path.basename(file_path)
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name'
        ).execute()
        
        return file
