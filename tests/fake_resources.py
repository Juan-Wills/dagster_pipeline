"""Fake resource implementations for testing without mocks

These are simple, fake implementations of resources that can be used
with AssetCheck-based testing.
"""

import io
import pandas as pd
from typing import Dict, List, Optional


class FakeGoogleDriveResource:
    """Fake Google Drive resource for testing."""
    
    def __init__(self):
        self.folders = {'raw_data': 'folder_123', 'processed_data': 'folder_456'}
        self.files = {}
        self.uploaded_files = []
        self.upload_calls = []
        self._list_files_override = None
    
    def find_folder_by_name(self, folder_name: str) -> Optional[str]:
        """Find folder by name."""
        return self.folders.get(folder_name)
    
    def create_folder_if_not_exists(self, folder_name: str) -> str:
        """Create or get folder."""
        if folder_name not in self.folders:
            self.folders[folder_name] = f'folder_{len(self.folders)}'
        return self.folders[folder_name]
    
    def list_files_in_folder(self, folder_id: str, mime_type: Optional[str] = None) -> List[Dict]:
        """List files in folder."""
        # Allow override for testing
        if self._list_files_override is not None:
            return self._list_files_override
        
        if folder_id == 'folder_123':  # raw_data folder
            return [
                {'id': 'file1', 'name': 'test1.csv'},
                {'id': 'file2', 'name': 'test2.csv'}
            ]
        elif folder_id == 'folder_456':  # processed_data folder
            return []
        return []
    
    def get_file_content(self, file_id: str) -> io.BytesIO:
        """Get file content."""
        # Return sample CSV with enough rows for transformation
        sample_csv = "Name,Age,City\nJohn,30,NYC\nJane,25,LA\nBob,35,SF\nAlice,28,CHI\n"
        return io.BytesIO(sample_csv.encode('utf-8'))
    
    def upload_file_from_memory(self, content, file_name: str, 
                                folder_id: str, mime_type: str = 'text/csv',
                                replace_if_exists: bool = False) -> Dict:
        """Upload file from memory."""
        # Check if file exists
        existing_files = self.list_files_in_folder(folder_id)
        existing = next((f for f in existing_files if f['name'] == file_name), None)
        
        action = 'replaced' if existing and replace_if_exists else 'created'
        file_id = existing['id'] if existing else f'uploaded_{len(self.uploaded_files)}'
        
        file_info = {
            'name': file_name,
            'id': file_id,
            'action': action,
            'status': 'success'
        }
        self.uploaded_files.append(file_info)
        self.upload_calls.append((file_name, folder_id))
        return file_info
    
    def assert_called(self):
        """Mock-like assertion for compatibility."""
        assert len(self.upload_calls) > 0, "upload_file_from_memory was not called"


class FakeDuckDBResource:
    """Fake DuckDB resource for testing."""
    
    def __init__(self):
        self.tables = {}
    
    def execute_query(self, query: str) -> None:
        """Execute query."""
        # Extract table name from CREATE TABLE queries if needed
        if 'CREATE TABLE' in query.upper():
            # Simple extraction for testing
            parts = query.split()
            if 'TABLE' in [p.upper() for p in parts]:
                idx = [p.upper() for p in parts].index('TABLE')
                if idx + 1 < len(parts):
                    table_name = parts[idx + 1].strip('(').strip()
                    self.tables[table_name] = True
    
    def get_connection(self):
        """Get connection."""
        return self
    
    def register(self, name: str, df: pd.DataFrame):
        """Register a DataFrame as a table."""
        self.tables[name] = df
    
    def execute(self, query: str):
        """Execute a query and return results."""
        # Simple mock execution
        return self
    
    def fetchone(self):
        """Fetch one result."""
        return (0,)  # Return a tuple with a count
    
    def fetchall(self):
        """Fetch all results."""
        return []
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        return False


class FakePostgreSQLResource:
    """Fake PostgreSQL resource for testing."""
    
    def __init__(self):
        self.tables = {}
        self.connected = True
    
    def execute_query(self, query: str) -> None:
        """Execute query."""
        if 'CREATE TABLE' in query.upper():
            parts = query.split()
            if 'TABLE' in [p.upper() for p in parts]:
                idx = [p.upper() for p in parts].index('TABLE')
                if idx + 1 < len(parts):
                    table_name = parts[idx + 1].strip('(').strip()
                    self.tables[table_name] = True
    
    def get_connection(self):
        """Get connection."""
        return self
    
    def test_connection(self) -> bool:
        """Test connection."""
        return self.connected


class FakeMongoDBResource:
    """Fake MongoDB resource for testing."""
    
    def __init__(self):
        self.db = FakeMongoDatabase()
        self.connected = True
    
    def get_database(self):
        """Get database."""
        return self.db
    
    def test_connection(self) -> bool:
        """Test connection."""
        return self.connected


class FakeMongoDatabase:
    """Fake MongoDB database for testing."""
    
    def __init__(self):
        self.collections = {}
    
    def __getitem__(self, collection_name: str):
        """Get collection."""
        if collection_name not in self.collections:
            self.collections[collection_name] = FakeMongoCollection(collection_name)
        return self.collections[collection_name]


class FakeMongoCollection:
    """Fake MongoDB collection for testing."""
    
    def __init__(self, name: str):
        self.name = name
        self.documents = []
    
    def insert_many(self, documents: List[Dict]):
        """Insert many documents."""
        self.documents.extend(documents)
        
        # Return result object with inserted_ids
        class InsertResult:
            def __init__(self, count):
                self.inserted_ids = [f'id_{i}' for i in range(count)]
        
        return InsertResult(len(documents))
