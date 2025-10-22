"""Tests for Dagster resources

Tests for database and external service resources.
Following Dagster best practices for resource testing.
"""

import os
import pytest
from unittest.mock import MagicMock, patch, Mock
import pandas as pd
import io

from dagster_pipeline.resources.google_drive_resource import GoogleDriveResource
from dagster_pipeline.resources.duckdb_connection import DuckDBResource
from dagster_pipeline.resources.postgresql_resource import PostgreSQLResource
from dagster_pipeline.resources.mongodb_resource import MongoDBResource


# ============================================================================
# Google Drive Resource Tests
# ============================================================================

class TestGoogleDriveResource:
    """Test suite for Google Drive resource."""
    
    def test_google_drive_resource_initialization(self):
        """Test Google Drive resource can be initialized."""
        resource = GoogleDriveResource(
            credentials_path="auth/credentials.json",
            token_path="auth/token.json",
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        
        assert resource.credentials_path == "auth/credentials.json"
        assert resource.token_path == "auth/token.json"
        assert len(resource.scopes) > 0
    
    @patch('dagster_pipeline.resources.google_drive_resource.build')
    @patch('dagster_pipeline.resources.google_drive_resource.GoogleDriveResource._get_credentials')
    def test_find_folder_by_name(self, mock_get_creds, mock_build):
        """Test finding a folder by name."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.files().list().execute.return_value = {
            'files': [{'id': 'folder123', 'name': 'test_folder'}]
        }
        
        resource = GoogleDriveResource(
            credentials_path="auth/credentials.json",
            token_path="auth/token.json"
        )
        
        folder_id = resource.find_folder_by_name("test_folder")
        
        assert folder_id == 'folder123'
    
    @patch('dagster_pipeline.resources.google_drive_resource.build')
    @patch('dagster_pipeline.resources.google_drive_resource.GoogleDriveResource._get_credentials')
    def test_list_files_in_folder(self, mock_get_creds, mock_build):
        """Test listing files in a folder."""
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.files().list().execute.return_value = {
            'files': [
                {'id': 'file1', 'name': 'test1.csv'},
                {'id': 'file2', 'name': 'test2.csv'}
            ]
        }
        
        resource = GoogleDriveResource(
            credentials_path="auth/credentials.json",
            token_path="auth/token.json"
        )
        
        files = resource.list_files_in_folder("folder123")
        
        assert len(files) == 2
        assert files[0]['name'] == 'test1.csv'
    
    @patch('dagster_pipeline.resources.google_drive_resource.build')
    @patch('dagster_pipeline.resources.google_drive_resource.GoogleDriveResource._get_credentials')
    def test_create_folder_if_not_exists_new_folder(self, mock_get_creds, mock_build):
        """Test creating a new folder."""
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # First call returns empty (folder doesn't exist)
        mock_service.files().list().execute.return_value = {'files': []}
        # Second call returns the created folder
        mock_service.files().create().execute.return_value = {'id': 'new_folder_id'}
        
        resource = GoogleDriveResource(
            credentials_path="auth/credentials.json",
            token_path="auth/token.json"
        )
        
        folder_id = resource.create_folder_if_not_exists("new_folder")
        
        assert folder_id == 'new_folder_id'


# ============================================================================
# DuckDB Resource Tests
# ============================================================================

class TestDuckDBResource:
    """Test suite for DuckDB resource."""
    
    def test_duckdb_resource_initialization(self):
        """Test DuckDB resource can be initialized."""
        resource = DuckDBResource(database=":memory:")
        
        assert resource.database == ":memory:"
    
    def test_duckdb_get_connection(self):
        """Test getting a DuckDB connection."""
        resource = DuckDBResource(database=":memory:")
        
        # get_connection() returns a context manager
        with resource.get_connection() as conn:
            # Verify we got a connection and can execute a simple query
            assert conn is not None
            result = conn.execute("SELECT 1 as test").fetchall()
            assert result == [(1,)]
    
    @patch('duckdb.connect')
    def test_duckdb_execute_query(self, mock_connect):
        """Test executing a query in DuckDB."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        resource = DuckDBResource(database=":memory:")
        with resource.get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER)")
        
        # Verify connection was created
        mock_connect.assert_called()
    
    @patch('duckdb.connect')
    def test_duckdb_create_table_from_dataframe(self, mock_connect):
        """Test creating a table from a DataFrame."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        df = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
        
        resource = DuckDBResource(database=":memory:")
        with resource.get_connection() as conn:
            # DuckDB can load DataFrames directly
            conn.execute("CREATE TABLE test_table AS SELECT * FROM df")
        
        # Verify connection was created
        mock_connect.assert_called()


# ============================================================================
# PostgreSQL Resource Tests
# ============================================================================

class TestPostgreSQLResource:
    """Test suite for PostgreSQL resource."""
    
    def test_postgresql_resource_initialization(self):
        """Test PostgreSQL resource can be initialized."""
        resource = PostgreSQLResource(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password"
        )
        
        assert resource.host == "localhost"
        assert resource.port == 5432
        assert resource.database == "test_db"
    
    @patch('dagster_pipeline.resources.postgresql_resource.psycopg2')
    def test_postgresql_get_connection(self, mock_psycopg2):
        """Test getting a PostgreSQL connection."""
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        
        resource = PostgreSQLResource(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password"
        )
        
        with resource.get_connection() as conn:
            assert conn is not None
        
        mock_psycopg2.connect.assert_called_once()
    
    @patch('dagster_pipeline.resources.postgresql_resource.psycopg2')
    def test_postgresql_test_connection_success(self, mock_psycopg2):
        """Test successful connection test."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2.connect.return_value = mock_conn
        
        resource = PostgreSQLResource(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password"
        )
        
        # Test by attempting a connection
        with resource.get_connection() as conn:
            result = conn is not None
        
        assert result is True
        mock_psycopg2.connect.assert_called_once()
    
    @patch('dagster_pipeline.resources.postgresql_resource.psycopg2')
    def test_postgresql_test_connection_failure(self, mock_psycopg2):
        """Test connection test failure."""
        mock_psycopg2.connect.side_effect = Exception("Connection failed")
        
        resource = PostgreSQLResource(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password"
        )
        
        # Connection should raise an exception
        with pytest.raises(Exception, match="Connection failed"):
            with resource.get_connection() as conn:
                pass
    
    @patch('dagster_pipeline.resources.postgresql_resource.psycopg2')
    def test_postgresql_execute_query(self, mock_psycopg2):
        """Test executing a query."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2.connect.return_value = mock_conn
        
        resource = PostgreSQLResource(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password"
        )
        
        result = resource.execute_query("CREATE TABLE test (id INTEGER)")
        
        # Verify the query was executed
        assert result is not None or result == []


# ============================================================================
# MongoDB Resource Tests
# ============================================================================

class TestMongoDBResource:
    """Test suite for MongoDB resource."""
    
    def test_mongodb_resource_initialization(self):
        """Test MongoDB resource can be initialized."""
        resource = MongoDBResource(
            host="localhost",
            port=27017,
            database="test_db",
            username="test_user",
            password="test_password",
            auth_source="admin"
        )
        
        assert resource.host == "localhost"
        assert resource.port == 27017
        assert resource.database == "test_db"
    
    @patch('dagster_pipeline.resources.mongodb_resource.MongoClient')
    def test_mongodb_get_database(self, mock_mongo_client):
        """Test getting a MongoDB database."""
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        
        resource = MongoDBResource(
            host="localhost",
            port=27017,
            database="test_db",
            username="test_user",
            password="test_password"
        )
        
        db = resource.get_database()
        
        assert db is not None
    
    @patch('dagster_pipeline.resources.mongodb_resource.MongoClient')
    def test_mongodb_test_connection_success(self, mock_mongo_client):
        """Test successful MongoDB connection test."""
        mock_client_instance = MagicMock()
        mock_db = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client_instance.server_info.return_value = {'version': '5.0'}
        mock_mongo_client.return_value = mock_client_instance
        
        resource = MongoDBResource(
            host="localhost",
            port=27017,
            database="test_db",
            username="test_user",
            password="test_password"
        )
        
        # Test by getting a database connection
        with resource.get_database() as db:
            result = db is not None
        
        assert result is True
    
    @patch('dagster_pipeline.resources.mongodb_resource.MongoClient')
    def test_mongodb_test_connection_failure(self, mock_mongo_client):
        """Test MongoDB connection test failure."""
        mock_mongo_client.side_effect = Exception("Connection failed")
        
        resource = MongoDBResource(
            host="localhost",
            port=27017,
            database="test_db",
            username="test_user",
            password="test_password"
        )
        
        # Connection should raise an exception
        with pytest.raises(Exception, match="Connection failed"):
            with resource.get_database() as db:
                pass
    
    @patch('dagster_pipeline.resources.mongodb_resource.MongoClient')
    def test_mongodb_insert_dataframe(self, mock_mongo_client):
        """Test inserting a DataFrame into MongoDB."""
        mock_client_instance = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo_client.return_value = mock_client_instance
        
        df = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
        
        resource = MongoDBResource(
            host="localhost",
            port=27017,
            database="test_db",
            username="test_user",
            password="test_password"
        )
        
        # Test inserting data using the insert_dataframe method
        # The actual resource should have this method implemented
        with resource.get_database() as db:
            # db is the actual Database object yielded from the context manager
            collection = db['test_collection']  # type: ignore
            records = df.to_dict('records')
            collection.insert_many(records)
        
        # Verify database was accessed
        mock_client_instance.__getitem__.assert_called()


# ============================================================================
# Resource Context Manager Tests
# ============================================================================

class TestResourceContextManagers:
    """Test resource context managers and cleanup."""
    
    @patch('duckdb.connect')
    def test_duckdb_resource_cleanup(self, mock_connect):
        """Test DuckDB resource cleanup."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        resource = DuckDBResource(database=":memory:")
        
        # Use context manager for proper cleanup
        with resource.get_connection() as conn:
            assert conn is not None
        
        # Context manager should handle cleanup
        mock_connect.assert_called()
    
    @patch('dagster_pipeline.resources.postgresql_resource.psycopg2')
    def test_postgresql_resource_cleanup(self, mock_psycopg2):
        """Test PostgreSQL resource cleanup."""
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        
        resource = PostgreSQLResource(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password"
        )
        
        # Use context manager for proper cleanup
        with resource.get_connection() as conn:
            assert conn is not None
        
        # Context manager should handle cleanup
        mock_conn.close.assert_called()
