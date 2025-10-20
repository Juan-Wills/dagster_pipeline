#!/usr/bin/env python3
"""
Test script to verify PostgreSQL and MongoDB connections.

Run this script to check if the database services are accessible.

Usage:
    python scripts/test_database_connections.py
"""

import sys
from typing import Tuple


def test_postgresql() -> Tuple[bool, str]:
    """Test PostgreSQL connection."""
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            database="appdb",
            user="appuser",
            password="apppassword"
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return True, f"✓ PostgreSQL connected successfully\n  Version: {version[:50]}..."
        
    except ImportError:
        return False, "✗ PostgreSQL: psycopg2 not installed. Run: pip install psycopg2-binary"
    except Exception as e:
        return False, f"✗ PostgreSQL connection failed: {str(e)}"


def test_mongodb() -> Tuple[bool, str]:
    """Test MongoDB connection."""
    try:
        from pymongo import MongoClient
        
        client = MongoClient(
            host="localhost",
            port=27017,
            username="admin",
            password="mongopassword",
            authSource="admin",
            serverSelectionTimeoutMS=5000
        )
        
        # Test connection
        server_info = client.server_info()
        version = server_info.get('version', 'unknown')
        
        # List databases
        db_list = client.list_database_names()
        
        client.close()
        
        return True, f"✓ MongoDB connected successfully\n  Version: {version}\n  Databases: {', '.join(db_list)}"
        
    except ImportError:
        return False, "✗ MongoDB: pymongo not installed. Run: pip install pymongo"
    except Exception as e:
        return False, f"✗ MongoDB connection failed: {str(e)}"


def test_docker_services() -> Tuple[bool, str]:
    """Check if Docker services are running."""
    try:
        import subprocess
        
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False, "✗ Docker: Unable to check running containers"
        
        containers = result.stdout.strip().split('\n')
        
        postgresql_running = 'postgresql_app' in containers
        mongodb_running = 'mongodb' in containers
        
        status = []
        if postgresql_running:
            status.append("✓ postgresql_app container is running")
        else:
            status.append("✗ postgresql_app container is NOT running")
            
        if mongodb_running:
            status.append("✓ mongodb container is running")
        else:
            status.append("✗ mongodb container is NOT running")
        
        all_running = postgresql_running and mongodb_running
        return all_running, "\n  ".join(status)
        
    except FileNotFoundError:
        return False, "✗ Docker: Docker command not found"
    except subprocess.TimeoutExpired:
        return False, "✗ Docker: Command timed out"
    except Exception as e:
        return False, f"✗ Docker: Error checking containers: {str(e)}"


def main():
    """Run all tests."""
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    print()
    
    # Check Docker services
    print("1. Checking Docker Services...")
    docker_ok, docker_msg = test_docker_services()
    print(f"  {docker_msg}")
    print()
    
    if not docker_ok:
        print("⚠️  Warning: Some Docker services are not running.")
        print("   Start them with: docker-compose up -d postgresql mongodb")
        print()
    
    # Test PostgreSQL
    print("2. Testing PostgreSQL Connection...")
    pg_ok, pg_msg = test_postgresql()
    print(f"  {pg_msg}")
    print()
    
    # Test MongoDB
    print("3. Testing MongoDB Connection...")
    mongo_ok, mongo_msg = test_mongodb()
    print(f"  {mongo_msg}")
    print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    if docker_ok and pg_ok and mongo_ok:
        print("✓ All tests passed! Databases are ready to use.")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        print()
        print("Troubleshooting tips:")
        print("  1. Ensure Docker services are running:")
        print("     docker-compose up -d")
        print()
        print("  2. Install required Python packages:")
        print("     pip install psycopg2-binary pymongo")
        print()
        print("  3. Check service logs:")
        print("     docker-compose logs postgresql mongodb")
        print()
        print("  4. Verify ports are not already in use:")
        print("     netstat -tulpn | grep -E '5433|27017'")
        return 1


if __name__ == "__main__":
    sys.exit(main())
