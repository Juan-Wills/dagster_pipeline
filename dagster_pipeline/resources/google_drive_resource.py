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
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, MediaIoBaseUpload

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
    
    def get_file_content(self, file_id: str) -> io.BytesIO:
        """Get file content from Google Drive as a BytesIO object (in-memory).
        
        Args:
            file_id: The Google Drive file ID
            
        Returns:
            BytesIO object containing the file content
        """
        service = self.get_service()
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        # Reset the file pointer to the beginning
        fh.seek(0)
        return fh
    
    def download_file_to_memory(self, file_id: str, file_name: str, download_path: str) -> str:
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
    
    def upload_file(self, file_path: str, folder_id: str, mime_type: str = 'text/csv', replace_if_exists: bool = True) -> Dict:
        """Upload a file to a Google Drive folder.
        
        Args:
            file_path: Path to the file to upload
            folder_id: ID of the parent folder
            mime_type: MIME type of the file
            replace_if_exists: If True, replaces existing file with same name. If False, creates new file.
            
        Returns:
            Dict containing the uploaded file's id, name, and action taken
        """
        service = self.get_service()
        
        file_name = os.path.basename(file_path)
        
        # Check if file already exists
        existing_file = self.find_file_in_folder(file_name, folder_id)
        action = 'created'
        
        if existing_file and replace_if_exists:
            # Delete the old file
            self.delete_file(existing_file['id'])
            action = 'replaced'
        elif existing_file and not replace_if_exists:
            # File exists and we don't want to replace - skip upload
            return {
                'id': existing_file['id'],
                'name': existing_file['name'],
                'action': 'skipped',
                'message': 'File already exists'
            }
        
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
        
        file['action'] = action
        return file
    
    def find_file_in_folder(self, file_name: str, folder_id: str) -> Optional[Dict]:
        """Find a file by name in a specific folder.
        
        Args:
            file_name: Name of the file to find
            folder_id: ID of the parent folder
            
        Returns:
            Dict containing file info if found, None otherwise
        """
        service = self.get_service()
        
        query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, modifiedTime)'
        ).execute()
        
        items = results.get('files', [])
        if not items:
            return None
        
        return items[0]
    
    def delete_file(self, file_id: str) -> None:
        """Delete a file from Google Drive.
        
        Args:
            file_id: ID of the file to delete
        """
        service = self.get_service()
        service.files().delete(fileId=file_id).execute()
    
    def upload_file_from_memory(self, file_content: io.BytesIO, file_name: str, folder_id: str, mime_type: str = 'text/csv', replace_if_exists: bool = True) -> Dict:
        """Upload a file to Google Drive from memory (BytesIO object).
        
        Args:
            file_content: BytesIO object containing the file data
            file_name: Name for the file in Google Drive
            folder_id: ID of the parent folder in Google Drive
            mime_type: MIME type of the file
            replace_if_exists: If True, replaces existing file with same name. If False, creates new file.
            
        Returns:
            Dict containing the uploaded file's id, name, and action taken
        """
        service = self.get_service()
        
        # Check if file already exists
        existing_file = self.find_file_in_folder(file_name, folder_id)
        action = 'created'
        
        if existing_file and replace_if_exists:
            # Delete the old file
            self.delete_file(existing_file['id'])
            action = 'replaced'
        elif existing_file and not replace_if_exists:
            # File exists and we don't want to replace - skip upload
            return {
                'id': existing_file['id'],
                'name': existing_file['name'],
                'action': 'skipped',
                'message': 'File already exists'
            }
        
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        # Reset file pointer to beginning
        file_content.seek(0)
        
        media = MediaIoBaseUpload(
            file_content,
            mimetype=mime_type,
            resumable=True
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name'
        ).execute()
        
        file['action'] = action
        return file
