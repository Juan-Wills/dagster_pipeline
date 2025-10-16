import os
import os.path
import io

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Folder where CSV files will be downloaded
DOWNLOAD_FOLDER = "downloaded_csv"
# Folder where processed files are located locally
UPLOAD_FOLDER = "processed_data"


def find_folder_by_name(service, folder_name):
    """Find a folder by name in Google Drive."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    
    items = results.get('files', [])
    if not items:
        print(f"No folder found with name '{folder_name}'")
        return None
    
    # Return the first matching folder
    return items[0]['id']


def download_csv_files_from_folder(service, folder_id, download_path):
    """Download all CSV files from a specific folder."""
    # Create download directory if it doesn't exist
    os.makedirs(download_path, exist_ok=True)
    
    # Query for CSV files in the folder
    query = f"'{folder_id}' in parents and mimeType='text/csv' and trashed=false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType)'
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        print(f"No CSV files found in the folder")
        return []
    
    downloaded_files = []
    print(f"Found {len(items)} CSV file(s) to download:")
    
    for item in items:
        file_id = item['id']
        file_name = item['name']
        file_path = os.path.join(download_path, file_name)
        
        print(f"  Downloading: {file_name}...")
        
        # Download file
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"    Progress: {int(status.progress() * 100)}%")
        
        # Write to file
        with open(file_path, 'wb') as f:
            f.write(fh.getvalue())
        
        downloaded_files.append(file_path)
        print(f"    ✓ Saved to: {file_path}")
    
    return downloaded_files


def create_folder_if_not_exists(service, folder_name):
    """Create a folder in Google Drive if it doesn't exist, return folder ID."""
    # First, check if folder already exists
    folder_id = find_folder_by_name(service, folder_name)
    
    if folder_id:
        print(f"Folder '{folder_name}' already exists (ID: {folder_id})")
        return folder_id
    
    # Create the folder
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    folder = service.files().create(
        body=file_metadata,
        fields='id'
    ).execute()
    
    folder_id = folder.get('id')
    print(f"Created folder '{folder_name}' (ID: {folder_id})")
    return folder_id


def upload_files_to_folder(service, folder_id, local_folder_path):
    """Upload all files from a local folder to a Google Drive folder."""
    if not os.path.exists(local_folder_path):
        print(f"Error: Local folder '{local_folder_path}' does not exist")
        return []
    
    # Get all files in the local folder
    files_to_upload = [f for f in os.listdir(local_folder_path) 
                       if os.path.isfile(os.path.join(local_folder_path, f))]
    
    if not files_to_upload:
        print(f"No files found in '{local_folder_path}' to upload")
        return []
    
    uploaded_files = []
    print(f"Found {len(files_to_upload)} file(s) to upload:")
    
    for file_name in files_to_upload:
        file_path = os.path.join(local_folder_path, file_name)
        
        print(f"  Uploading: {file_name}...")
        
        # Determine MIME type based on file extension
        mime_type = 'text/csv' if file_name.endswith('.csv') else 'application/octet-stream'
        
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
        
        try:
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name'
            ).execute()
            
            uploaded_files.append(file)
            print(f"    ✓ Uploaded: {file.get('name')} (ID: {file.get('id')})")
        
        except HttpError as error:
            print(f"    ✗ Error uploading {file_name}: {error}")
    
    return uploaded_files


def main():
    """Download CSV files from Google Drive 'raw_data' folder."""
    # Authentication process
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("auth/token.json"):
        creds = Credentials.from_authorized_user_file("auth/token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "auth/credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
        with open("auth/token.json", "w") as token:
            token.write(creds.to_json())

    # Call the service
    try:
        service = build("drive", "v3", credentials=creds)
        
        # Find the 'raw_data' folder
        print("Searching for 'raw_data' folder...")
        folder_id = find_folder_by_name(service, "raw_data")
        
        if not folder_id:
            print("Error: 'raw_data' folder not found in your Google Drive")
            return
        
        print(f"Found 'raw_data' folder (ID: {folder_id})")
        
        # Download CSV files from the folder
        downloaded_files = download_csv_files_from_folder(
            service, 
            folder_id, 
            DOWNLOAD_FOLDER
        )
        
        print(f"\n✓ Successfully downloaded {len(downloaded_files)} file(s)")
        
        # Upload processed files to Google Drive
        print("\n" + "="*60)
        print("Uploading processed files to Google Drive...")
        print("="*60)
        
        # Create or find the 'processed_data' folder
        processed_folder_id = create_folder_if_not_exists(service, "processed_data")
        
        # Upload files from local processed_data folder
        uploaded_files = upload_files_to_folder(
            service,
            processed_folder_id,
            UPLOAD_FOLDER
        )
        
        print(f"\n✓ Successfully uploaded {len(uploaded_files)} file(s)")
        
    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()