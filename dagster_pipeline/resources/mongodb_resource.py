"""MongoDB resource for Dagster application data

Handles connections to the MongoDB database.
"""

from contextlib import contextmanager
from typing import Generator, Dict, List, Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

from dagster import ConfigurableResource
from pydantic import Field


class MongoDBResource(ConfigurableResource):
    """Resource for interacting with MongoDB database."""
    
    host: str = Field(
        default="localhost",
        description="MongoDB host address"
    )
    port: int = Field(
        default=27017,
        description="MongoDB port number"
    )
    database: str = Field(
        default="dagster_pipeline",
        description="MongoDB database name"
    )
    username: str = Field(
        default="juan-wills",
        description="MongoDB username"
    )
    password: str = Field(
        default="juan1234",
        description="MongoDB password"
    )
    auth_source: str = Field(
        default="admin",
        description="Authentication database"
    )
    
    def get_client(self) -> MongoClient:
        """Get a MongoDB client.
        
        Returns:
            MongoClient: MongoDB client object
        """
        return MongoClient(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            authSource=self.auth_source
        )
    
    @contextmanager
    def get_database(self) -> Generator[Database, None, None]:
        """Get a MongoDB database connection.
        
        Yields:
            Database: MongoDB database object
            
        Example:
            with mongodb.get_database() as db:
                collection = db['my_collection']
                result = collection.find_one({'key': 'value'})
        """
        client = self.get_client()
        try:
            yield client[self.database]
        finally:
            client.close()
    
    @contextmanager
    def get_collection(self, collection_name: str) -> Generator[Collection, None, None]:
        """Get a MongoDB collection.
        
        Args:
            collection_name: Name of the collection
            
        Yields:
            Collection: MongoDB collection object
            
        Example:
            with mongodb.get_collection('users') as collection:
                users = collection.find({'active': True})
        """
        with self.get_database() as db:
            yield db[collection_name]
    
    def insert_one(self, collection_name: str, document: Dict) -> str:
        """Insert a single document into a collection.
        
        Args:
            collection_name: Name of the collection
            document: Document to insert
            
        Returns:
            String representation of the inserted document's ID
        """
        with self.get_collection(collection_name) as collection:
            result = collection.insert_one(document)
            return str(result.inserted_id)
    
    def insert_many(self, collection_name: str, documents: List[Dict]) -> List[str]:
        """Insert multiple documents into a collection.
        
        Args:
            collection_name: Name of the collection
            documents: List of documents to insert
            
        Returns:
            List of inserted document IDs as strings
        """
        with self.get_collection(collection_name) as collection:
            result = collection.insert_many(documents)
            return [str(id) for id in result.inserted_ids]
    
    def find_one(self, collection_name: str, filter: Dict) -> Optional[Dict]:
        """Find a single document in a collection.
        
        Args:
            collection_name: Name of the collection
            filter: Query filter
            
        Returns:
            Document if found, None otherwise
        """
        with self.get_collection(collection_name) as collection:
            return collection.find_one(filter)
    
    def find_many(self, collection_name: str, filter: Dict = None, limit: int = 0) -> List[Dict]:
        """Find multiple documents in a collection.
        
        Args:
            collection_name: Name of the collection
            filter: Query filter (empty dict or None for all documents)
            limit: Maximum number of documents to return (0 for no limit)
            
        Returns:
            List of documents
        """
        filter = filter or {}
        with self.get_collection(collection_name) as collection:
            cursor = collection.find(filter)
            if limit > 0:
                cursor = cursor.limit(limit)
            return list(cursor)
    
    def update_one(self, collection_name: str, filter: Dict, update: Dict) -> int:
        """Update a single document in a collection.
        
        Args:
            collection_name: Name of the collection
            filter: Query filter to find the document
            update: Update operations
            
        Returns:
            Number of documents modified
        """
        with self.get_collection(collection_name) as collection:
            result = collection.update_one(filter, update)
            return result.modified_count
    
    def update_many(self, collection_name: str, filter: Dict, update: Dict) -> int:
        """Update multiple documents in a collection.
        
        Args:
            collection_name: Name of the collection
            filter: Query filter to find documents
            update: Update operations
            
        Returns:
            Number of documents modified
        """
        with self.get_collection(collection_name) as collection:
            result = collection.update_many(filter, update)
            return result.modified_count
    
    def delete_one(self, collection_name: str, filter: Dict) -> int:
        """Delete a single document from a collection.
        
        Args:
            collection_name: Name of the collection
            filter: Query filter to find the document
            
        Returns:
            Number of documents deleted
        """
        with self.get_collection(collection_name) as collection:
            result = collection.delete_one(filter)
            return result.deleted_count
    
    def delete_many(self, collection_name: str, filter: Dict) -> int:
        """Delete multiple documents from a collection.
        
        Args:
            collection_name: Name of the collection
            filter: Query filter to find documents
            
        Returns:
            Number of documents deleted
        """
        with self.get_collection(collection_name) as collection:
            result = collection.delete_many(filter)
            return result.deleted_count
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists in the database.
        
        Args:
            collection_name: Name of the collection to check
            
        Returns:
            True if collection exists, False otherwise
        """
        with self.get_database() as db:
            return collection_name in db.list_collection_names()
    
    def create_collection(self, collection_name: str) -> bool:
        """Create a new collection in the database.
        
        Args:
            collection_name: Name of the collection to create
            
        Returns:
            True if collection was created, False if it already exists
        """
        with self.get_database() as db:
            if collection_name not in db.list_collection_names():
                db.create_collection(collection_name)
                return True
            return False
    
    def drop_collection(self, collection_name: str) -> bool:
        """Drop a collection from the database.
        
        Args:
            collection_name: Name of the collection to drop
            
        Returns:
            True if collection was dropped, False if it didn't exist
        """
        with self.get_database() as db:
            if collection_name in db.list_collection_names():
                db.drop_collection(collection_name)
                return True
            return False
    
    def insert_dataframe(self, collection_name: str, df, replace: bool = False) -> int:
        """Insert a pandas DataFrame into a MongoDB collection.
        
        Args:
            collection_name: Name of the collection
            df: pandas DataFrame to insert
            replace: If True, drops existing collection first
            
        Returns:
            Number of documents inserted
        """
        if replace:
            self.drop_collection(collection_name)
        
        # Convert DataFrame to list of dictionaries
        documents = df.to_dict('records')
        
        if documents:
            return len(self.insert_many(collection_name, documents))
        return 0
