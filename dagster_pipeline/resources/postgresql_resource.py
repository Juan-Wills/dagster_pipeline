"""PostgreSQL resource for Dagster application data

Handles connections to the application PostgreSQL database.
"""

import psycopg2
from contextlib import contextmanager
from typing import Generator

from dagster import ConfigurableResource
from pydantic import Field


class PostgreSQLResource(ConfigurableResource):
    """Resource for interacting with PostgreSQL application database."""
    
    host: str = Field(
        default="localhost",
        description="PostgreSQL host address"
    )
    port: int = Field(
        default=5433,
        description="PostgreSQL port number"
    )
    database: str = Field(
        default="app_postgres_db",
        description="PostgreSQL database name"
    )
    user: str = Field(
        default="juan-wills",
        description="PostgreSQL username"
    )
    password: str = Field(
        default="juan1234",
        description="PostgreSQL password"
    )
    
    @contextmanager
    def get_connection(self) -> Generator:
        """Get a PostgreSQL database connection.
        
        Yields:
            psycopg2.connection: Database connection object
            
        Example:
            with postgresql.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM my_table")
                    results = cur.fetchall()
        """
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password
        )
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters for safe parameterization
            
        Returns:
            List of tuples containing query results
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()
    
    def execute_command(self, command: str, params: tuple = None) -> int:
        """Execute an INSERT, UPDATE, or DELETE command.
        
        Args:
            command: SQL command string
            params: Command parameters for safe parameterization
            
        Returns:
            Number of rows affected
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(command, params)
                return cur.rowcount
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = %s
            );
        """
        result = self.execute_query(query, (table_name,))
        return result[0][0] if result else False
    
    def create_table_from_dataframe(self, df, table_name: str, if_exists: str = 'replace'):
        """Create a table from a pandas DataFrame.
        
        Args:
            df: pandas DataFrame to insert
            table_name: Name of the table to create
            if_exists: How to behave if table exists ('fail', 'replace', 'append')
        """
        from sqlalchemy import create_engine
        
        engine = create_engine(
            f'postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'
        )
        
        df.to_sql(table_name, engine, if_exists=if_exists, index=False)
        engine.dispose()
